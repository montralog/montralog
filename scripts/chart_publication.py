"""Validate newly indexed images and mark retired chart metadata without rewriting archives."""
import io
import tarfile
import yaml

RETIRED = {'0.5.1-rc.1': 'Retired: references an unpublished RC image. Use chart 0.8.1; back up before upgrading.'}


def validate_chart_image(archive, resolve_digest):
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as package:
        values_file = next((m for m in package.getmembers() if m.name.count('/') == 1 and m.name.endswith('/values.yaml')), None)
        if values_file is None or values_file.size > 1024 * 1024:
            raise ValueError('Chart must include bounded values.yaml')
        values = yaml.safe_load(package.extractfile(values_file))
    image = values.get('image', {})
    if image.get('repository') != 'ghcr.io/montralog/montralog':
        raise ValueError('Chart must reference the public ghcr.io/montralog/montralog image')
    reference = image['repository'] + ':' + str(image.get('tag', ''))
    actual = resolve_digest(reference)  # anonymous lookup; errors block publication
    if image.get('digest') and image['digest'] != actual:
        raise ValueError('Chart image digest differs from the public registry')
    return reference, actual


def mark_retired(index):
    for entry in index.get('entries', {}).get('montralog', []):
        if entry.get('version') in RETIRED:
            entry['deprecated'] = True
            entry['description'] = RETIRED[entry['version']]
    return index
