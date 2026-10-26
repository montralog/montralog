"""Real storage transitions and concurrent-worker probes; no external delivery."""
import json
import os
import socket
import threading
import time
import unittest
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from cryptography.fernet import Fernet
import test_gateway
from montralog import notifications, outbound, secret_store, storage


class TransportDeadlineTests(unittest.TestCase):
    def test_trickling_response_cannot_extend_total_delivery_deadline(self):
        # Real loopback socket: each byte arrives within the socket timeout,
        # but the whole response must still stop at the transport deadline.
        listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(3)
        port=listener.getsockname()[1]
        finished=threading.Event();failures=[]
        def trickle():
            try:
                with listener.accept()[0] as peer:
                    peer.settimeout(2);peer.recv(8192)
                    peer.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 100\r\nConnection: close\r\n\r\n')
                    for _ in range(100):
                        if finished.wait(.03):break
                        peer.sendall(b'x')
            except OSError:
                pass  # Deadline closes the peer while it is still streaming.
            except BaseException as error:
                failures.append(error)
        worker=threading.Thread(target=trickle,daemon=True);worker.start()
        started=time.monotonic();received=b''
        try:
            with outbound.open_request(urllib.request.Request(f'http://127.0.0.1:{port}/'),timeout=.3,
                                       private_origins=(f'127.0.0.1:{port}',)) as response:
                try:received=response.read(100)
                except (OSError,ValueError,outbound.DestinationError):pass
        finally:
            finished.set();worker.join(3)
        self.assertLess(time.monotonic()-started,1.5)
        self.assertLess(len(received),100)
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures,[])


class DeliveryReliabilityTests(unittest.TestCase):
    def setUp(self):
        test_gateway.GatewayTests.setUp(self)
        self.crypto=patch.dict(os.environ,{'MONTRALOG_ENCRYPTION_KEY':Fernet.generate_key().decode()})
        self.crypto.start()
        self.addCleanup(self.crypto.stop)

    tearDown=test_gateway.GatewayTests.tearDown

    def channel(self):
        with storage.database() as db:
            db.execute('INSERT INTO notification_channels(id,name,kind,secret,enabled,created_at) VALUES (?,?,?,?,?,?)',
                       ('channel','Synthetic route','slack',secret_store.seal('https://hooks.slack.com/services/FIXTURE/ONLY/not-a-secret'),1,time.time()))

    def rule(self,for_seconds=0):
        self.channel()
        definition={'source':'metric','metric':'memory','op':'gt','threshold':10,'for_seconds':for_seconds,'channels':['channel']}
        with storage.database() as db:
            db.execute('INSERT INTO alert_rules(id,name,definition,enabled,created_at) VALUES (?,?,?,?,?)',
                       ('rule','Fixture threshold',json.dumps(definition),1,time.time()))

    def queued(self,count=1):
        self.channel()
        with storage.database() as db:
            for index in range(count):
                db.execute('INSERT INTO notification_outbox(id,channel_id,message,status,attempts,next_attempt,created_at,last_error) VALUES (?,?,?,?,?,?,?,?)',
                           (f'queued-{index:03}','channel',f'Synthetic delivery {index}','pending',0,0,0,''))

    def row(self):
        with storage.database() as db:
            return dict(db.execute('SELECT * FROM notification_outbox ORDER BY id LIMIT 1').fetchone())

    def test_outage_keeps_firing_identity_and_recovery_emits_resolution_once(self):
        self.rule()
        with patch.object(notifications,'evaluate',side_effect=[(20,'sample'),(None,'backend unavailable'),(0,'recovered'),(0,'still normal')]), patch.object(notifications,'send_slack') as sender:
            for _ in range(4):notifications.tick()
            self.assertEqual(sender.call_count,2)
        with storage.database() as db:
            states=[row[0] for row in db.execute('SELECT state FROM notification_inbox ORDER BY created_at')]
            self.assertEqual(states,['firing','normal'])
            state=db.execute("SELECT state,last_known_state FROM alert_states WHERE rule_id='rule'").fetchone()
            self.assertEqual((state[0],state[1]),('normal','normal'))

    def test_outage_does_not_repeat_firing_when_condition_remains_bad(self):
        self.rule()
        with patch.object(notifications,'evaluate',side_effect=[(20,'sample'),(None,'unavailable'),(20,'recovered'),(20,'still bad')]), patch.object(notifications,'send_slack') as sender:
            for _ in range(4):notifications.tick()
            self.assertEqual(sender.call_count,1)
        with storage.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM notification_inbox').fetchone()[0],1)
            state=db.execute("SELECT state,last_known_state FROM alert_states WHERE rule_id='rule'").fetchone()
            self.assertEqual((state[0],state[1]),('firing','firing'))

    def test_unknown_time_does_not_satisfy_pending_wait(self):
        self.rule(for_seconds=10)
        with patch.object(notifications,'send_slack') as sender:
            for instant,value in ((100,20),(105,None),(200,20)):
                with patch.object(notifications.time,'time',return_value=instant), patch.object(notifications,'evaluate',return_value=(value,'synthetic')):
                    notifications.tick()
            with storage.database() as db:
                row=db.execute("SELECT state,since_at FROM alert_states WHERE rule_id='rule'").fetchone()
                self.assertEqual((row[0],row[1]),('pending',200))
            self.assertEqual(sender.call_count,0)
            with patch.object(notifications.time,'time',return_value=211), patch.object(notifications,'evaluate',return_value=(20,'synthetic')):
                notifications.tick()
            self.assertEqual(sender.call_count,1)

    def test_concurrent_evaluators_create_only_one_firing_transition(self):
        self.rule()
        together=threading.Barrier(2)
        def evaluate(_):
            together.wait(timeout=15)
            return 20,'simultaneous sample'
        with patch.object(notifications,'evaluate',side_effect=evaluate), patch.object(notifications,'send_slack') as sender:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(notifications.tick) for _ in range(2)]
                for future in futures:future.result(timeout=30)
            self.assertEqual(sender.call_count,1)
        with storage.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM notification_inbox').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM notification_outbox').fetchone()[0],1)

    def test_live_lease_prevents_concurrent_worker_duplicate_send(self):
        self.queued()
        started=threading.Event();release=threading.Event()
        def send(*_):
            started.set()
            if not release.wait(timeout=15):raise RuntimeError('Test did not release the simulated sender')
        with patch.object(notifications,'send_slack',side_effect=send) as sender:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(notifications.deliver)
                try:
                    self.assertTrue(started.wait(timeout=10))
                    second=pool.submit(notifications.deliver)
                    second.result(timeout=10)
                    self.assertEqual(sender.call_count,1)
                finally:release.set()
                first.result(timeout=15)
        row=self.row()
        self.assertEqual((row['status'],row['attempts'],row['lease_owner'],row['lease_until']),('sent',1,'',0))

    def test_expired_worker_lease_is_recovered_but_unexpired_lease_is_not(self):
        self.queued()
        with storage.database() as db:
            db.execute('UPDATE notification_outbox SET lease_owner=?,lease_until=?',('crashed-worker',time.time()+120))
        with patch.object(notifications,'send_slack') as sender:
            notifications.deliver();self.assertEqual(sender.call_count,0)
            with storage.database() as db:db.execute('UPDATE notification_outbox SET lease_until=0')
            notifications.deliver();self.assertEqual(sender.call_count,1)
        self.assertEqual(self.row()['status'],'sent')

    def test_stale_acknowledgement_cannot_overwrite_a_newer_lease(self):
        self.queued()
        def newer_owner(*_):
            with storage.database() as db:
                db.execute('UPDATE notification_outbox SET lease_owner=?,lease_until=?,attempts=2',('replacement',time.time()+120))
        with patch.object(notifications,'send_slack',side_effect=newer_owner):notifications.deliver()
        row=self.row()
        self.assertEqual((row['status'],row['attempts'],row['lease_owner']),('pending',2,'replacement'))

    def test_operator_cancellation_is_not_overwritten_by_inflight_delivery(self):
        self.queued()
        def cancel(*_):
            with storage.database() as db:db.execute("UPDATE notification_outbox SET status='cancelled'")
        with patch.object(notifications,'send_slack',side_effect=cancel):notifications.deliver()
        self.assertEqual(self.row()['status'],'cancelled')

    def test_persisted_retry_limit_and_secret_safe_terminal_failure(self):
        self.queued()
        with patch.object(notifications,'send_slack',side_effect=OSError('never expose private provider detail')) as sender:
            for attempt in range(5):
                with storage.database() as db:db.execute('UPDATE notification_outbox SET next_attempt=0')
                notifications.deliver()
                self.assertEqual(self.row()['attempts'],attempt+1)
            notifications.deliver()
            self.assertEqual(sender.call_count,5)
        row=self.row()
        self.assertEqual(row['status'],'failed')
        self.assertNotIn('private provider detail',row['last_error'])
        self.assertNotIn('hooks.slack.com',row['last_error'])
        self.assertEqual((row['lease_owner'],row['lease_until']),('',0))

    def test_delivery_cycle_remains_bounded_and_leaves_remaining_records_due(self):
        self.queued(count=25)
        with patch.object(notifications,'send_slack') as sender:
            notifications.deliver()
            self.assertEqual(sender.call_count,notifications.DELIVERY_BATCH_LIMIT)
            with storage.database() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM notification_outbox WHERE status='pending'").fetchone()[0],5)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM notification_outbox WHERE lease_owner!=''").fetchone()[0],0)
            notifications.deliver()
            self.assertEqual(sender.call_count,25)
