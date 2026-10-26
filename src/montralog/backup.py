"""Private SQLite snapshots with integrity and silo identity verification."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from contextlib import closing
from . import storage
from .config import VERSION
from .tenancy import tenant_id,key_fingerprint


def private_file(path):
    path=Path(path)
    if os.name=='posix':
        info=path.parent.stat()
        if info.st_mode & 0o022 or info.st_uid!=os.geteuid():
            raise ValueError('Backup destination directory must be private to its operator.')
    return os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def create(destination):
    if storage.postgres_enabled():raise ValueError('Use PostgreSQL native backups/PITR; this command is SQLite only.')
    destination=Path(destination)
    manifest=Path(str(destination)+'.manifest.json')
    fd=private_file(destination)
    manifest_created=False
    try:
        metadata_fd=private_file(manifest);manifest_created=True
        os.close(fd);fd=None
        try:
            with storage.database() as source,closing(sqlite3.connect(destination)) as target:
                source.backup(target)
            metadata={'format':'montralog-snapshot-v1','sha256':digest(destination),'tenant_id':tenant_id(),
                'key_fingerprint':key_fingerprint(),'schema':storage.SCHEMA_VERSION,'application':VERSION,
                'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            with os.fdopen(metadata_fd,'w',encoding='utf-8') as output:
                json.dump(metadata,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
        except BaseException:
            # Metadata contains no encryption key, but is private alongside data.
            try:os.close(metadata_fd)
            except OSError:pass
            raise
        verify(destination)
        return metadata
    except BaseException:
        if fd is not None:os.close(fd)
        destination.unlink(missing_ok=True)
        if manifest_created:manifest.unlink(missing_ok=True)
        raise


def verify(source):
    source=Path(source)
    metadata=json.loads(Path(str(source)+'.manifest.json').read_text(encoding='utf-8'))
    if metadata.get('format')!='montralog-snapshot-v1' or metadata.get('sha256')!=digest(source):
        raise ValueError('Backup manifest or checksum verification failed.')
    if metadata.get('tenant_id')!=tenant_id() or metadata.get('key_fingerprint')!=key_fingerprint():
        raise ValueError('Backup belongs to a different silo or encryption key.')
    if not isinstance(metadata.get('schema'),int) or metadata['schema']>storage.SCHEMA_VERSION:
        raise ValueError('Backup schema is not supported.')
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Backup SQLite integrity check failed.')
        version=db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        binding=db.execute('SELECT tenant_id,key_fingerprint FROM deployment_identity WHERE id=1').fetchone()
        if version!=metadata['schema'] or not binding or binding[0]!=tenant_id() or binding[1]!=key_fingerprint():
            raise ValueError('Backup contents do not match its manifest or silo.')
        from .secret_store import reveal
        for table in ('data_sources','notification_channels'):
            for row in db.execute('SELECT secret FROM '+table):reveal(row[0])
        for row in db.execute('SELECT config FROM identity_providers'):reveal(json.loads(row[0]).get('client_secret',''))
    return metadata


def restore(source,destination):
    metadata=verify(source)
    destination=Path(destination)
    fd=private_file(destination)
    try:
        with os.fdopen(fd,'wb') as target,Path(source).open('rb') as original:
            shutil.copyfileobj(original,target,1024*1024);target.flush();os.fsync(target.fileno())
        if digest(destination)!=metadata['sha256']:raise ValueError('Restored backup checksum differs.')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return metadata
