import time
import unittest
import test_gateway
from montralog import storage
from montralog.queries import query_view

class LogPaginationTests(unittest.TestCase):
    setUp=test_gateway.GatewayTests.setUp
    tearDown=test_gateway.GatewayTests.tearDown

    def seed(self,count=201):
        stamp=time.time()-5
        with storage.database() as db:
            for i in range(count):
                db.execute("INSERT INTO logs(time,received,service,environment,severity,message,pattern,trace_id,attributes) VALUES (?,?,?,?,?,?,?,?,?)",(stamp,stamp,'api','test','INFO',str(i),'fixture','','{}'))

    def test_cursor_pages_cover_tied_timestamps_without_duplicates(self):
        self.seed()
        params={'minutes':'60'}
        seen=[]
        while True:
            page=query_view('logs',params)
            seen.extend(r['id'] for r in page['items'])
            if not page['has_more']:
                self.assertIsNone(page['next_cursor'])
                break
            params={**params,'cursor':page['next_cursor']}
        self.assertEqual(len(seen),201)
        self.assertEqual(len(set(seen)),201)
        self.assertEqual(seen,sorted(seen,reverse=True))

    def test_new_arrivals_do_not_shift_following_pages(self):
        self.seed()
        first=query_view('logs',{'minutes':'60'})
        stamp=time.time()+0.001
        with storage.database() as db:
            db.execute("INSERT INTO logs(time,received,service,environment,severity,message,pattern,trace_id,attributes) VALUES (?,?,?,?,?,?,?,?,?)",(stamp,stamp,'api','test','INFO','new','fixture','','{}'))
        second=query_view('logs',{'minutes':'60','cursor':first['next_cursor']})
        self.assertFalse(set(r['id'] for r in first['items']) & set(r['id'] for r in second['items']))
        self.assertTrue(all(r['message']!='new' for r in second['items']))

    def test_cursor_rejects_changed_filters_and_invalid_values(self):
        self.seed()
        first=query_view('logs',{'minutes':'60','service':'api'})
        for params in [{'minutes':'60','service':'other','cursor':first['next_cursor']},
                       {'minutes':'15','service':'api','cursor':first['next_cursor']},
                       {'minutes':'60','cursor':'not-a-valid-cursor'},
                       {'minutes':'60','cursor':'x'*600}]:
            with self.assertRaises(ValueError):query_view('logs',params)

    def test_lookahead_handles_exact_page_and_legacy_offset(self):
        self.seed(200)
        first=query_view('logs',{'minutes':'60'})
        last=query_view('logs',{'minutes':'60','offset':'100'})
        self.assertTrue(first['has_more'])
        self.assertEqual(len(last['items']),100)
        self.assertFalse(last['has_more'])

    def test_backdated_new_logs_are_excluded_by_snapshot_maximum_id(self):
        self.seed()
        first=query_view('logs',{'minutes':'60'})
        stamp=first['items'][-1]['time']-1
        with storage.database() as db:
            db.execute("INSERT INTO logs(time,received,service,environment,severity,message,pattern,trace_id,attributes) VALUES (?,?,?,?,?,?,?,?,?)",(stamp,time.time(),'api','test','INFO','late arrival','fixture','','{}'))
        cursor=first['next_cursor'];remaining=[]
        while cursor:
            page=query_view('logs',{'minutes':'60','cursor':cursor})
            remaining.extend(page['items']);cursor=page['next_cursor']
        self.assertEqual(len(remaining),101)
        self.assertTrue(all(row['message']!='late arrival' for row in remaining))
