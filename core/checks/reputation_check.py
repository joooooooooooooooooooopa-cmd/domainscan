"""P-093..P-108: Reputation check - Wayback, indexation."""
import asyncio
import httpx


async def check_reputation(domain: str) -> dict:
    result = {
        'wayback_snapshots_count': 0,
        'wayback_first_snapshot': None,
        'wayback_last_snapshot': None,
        'wayback_available': False,
    }

    try:
        wb_cdx, wb_avail = await asyncio.gather(
            _check_wayback(domain),
            _check_wayback_availability(domain),
            return_exceptions=True,
        )
        if isinstance(wb_cdx, dict):
            result.update(wb_cdx)
        if isinstance(wb_avail, bool):
            result['wayback_available'] = wb_avail
    except Exception:
        pass

    return result


async def _check_wayback(domain: str) -> dict:
    result = {
        'wayback_snapshots_count': 0,
        'wayback_first_snapshot': None,
        'wayback_last_snapshot': None,
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "DomainScan/1.0"},
            ) as client:
                resp = await client.get(
                    'https://web.archive.org/cdx/search/cdx',
                    params={
                        'url': f'{domain}/*',
                        'output': 'json',
                        'fl': 'timestamp',
                        'collapse': 'timestamp:8',
                        'limit': '200',
                        'fastLatest': 'true',
                    }
                )
                if resp.status_code == 200:
                    text = resp.text.strip()
                    if not text or text == '[]':
                        break
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 1:
                        timestamps = [row[0] for row in data[1:] if row]
                        result['wayback_snapshots_count'] = len(timestamps)
                        if timestamps:
                            result['wayback_first_snapshot'] = timestamps[0]
                            result['wayback_last_snapshot'] = timestamps[-1]
                        return result
                break
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            break
        except Exception:
            break

    return result


async def _check_wayback_availability(domain: str) -> bool:
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "DomainScan/1.0"},
        ) as client:
            resp = await client.get(
                'https://archive.org/wayback/available',
                params={'url': domain}
            )
            if resp.status_code == 200:
                data = resp.json()
                snapshots = data.get('archived_snapshots', {})
                return bool(snapshots.get('closest'))
    except Exception:
        pass
    return False
