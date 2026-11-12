"""Evidence-preserving injury/depth joins. Never turn an injury into a starter guess."""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parent
PRACTICE = {'F': 'Full Participation in Practice', 'L': 'Limited Participation in Practice', 'D': 'Did Not Participate In Practice'}
OFFENSE = {'QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT'}
DEFENSE = {'DE', 'DT', 'NT', 'DL', 'EDGE', 'OLB', 'LB', 'ILB', 'MLB', 'WLB', 'SAM', 'WILL', 'MIKE', 'SLB', 'RUSH', 'CB', 'NB', 'NCB', 'S', 'SS', 'FS', 'DB', 'LDE', 'LDT', 'RDT', 'RDE', 'LOLB', 'LILB', 'RILB', 'ROLB'}
ALIASES = {('NE', 'Kevin Byard III'): 'Kevin Byard', ('CLE', 'Ronnie Hickman'): 'Ronnie Hickman Jr.', ('AZ', 'Mack Wilson Sr.'): 'Mack Wilson'}


def norm(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', value)


def load_sources():
    return {r['id']: r for r in json.loads((ROOT / 'sources/registry.json').read_text())}


def parse_injuries(text):
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        fields = line.split('|')
        if len(fields) != 6:
            raise ValueError('Malformed injury transcription: ' + line)
        team, player, pos, injury, practice, game = fields
        if practice not in PRACTICE or game not in ('', 'Out', 'Questionable', 'Doubtful'):
            raise ValueError('Unknown designation: ' + line)
        rows.append({'id': f'I-{team}-{len(rows)+1:03}', 'team': team, 'player': player, 'position': pos,
                     'injury': injury or None, 'practice_status': PRACTICE[practice], 'game_status': game or None,
                     'source_ids': ['A958-NFL-INJURIES'], 'status': 'Source compared',
                     'availability': 'Out' if game == 'Out' else 'Uncertain' if game else 'Not designated',
                     'note': 'Blank injury/game cells are source blanks; not a clean bill of health or final active list.'})
    if len({(r['team'], norm(r['player'])) for r in rows}) != len(rows):
        raise ValueError('Duplicate team/player injury row')
    return rows


def parse_depth(text):
    rows = []
    counters = Counter()
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        fields = line.split('|')
        if len(fields) != 8:
            raise ValueError('Malformed depth transcription: ' + line)
        team, unit, position, *players = fields
        if unit not in ('Offense', 'Defense', 'Special Teams') or position not in OFFENSE | DEFENSE | {'K', 'P', 'H', 'LS', 'PR', 'KR', 'KOR'}:
            raise ValueError('Unknown unit/position: ' + line)
        expected = 'Offense' if position in OFFENSE else 'Defense' if position in DEFENSE else 'Special Teams'
        if unit != expected:
            raise ValueError('Position/unit mismatch: ' + line)
        counters[(team, unit, position)] += 1
        rows.append({'id': f'D-{team}-{len(rows)+1:03}', 'team': team, 'unit': unit, 'position': position,
                     'slot': counters[(team, unit, position)], 'players': players,
                     'source_ids': ['A958-' + team + '-DEPTH'], 'status': 'Source compared',
                     'authority_note': 'Club-published printed order; not a confirmed starter list.'})
    return rows


def player_name(team, name):
    return ALIASES.get((team, name), name)


def join_depth(depth, injuries):
    lookup = {(r['team'], norm(r['player'])): r for r in injuries}
    joined, unmatched = [], []
    for row in depth:
        entries = []
        for col, cell in enumerate(row['players'], 1):
            if not cell:
                entries.append(None)
                continue
            names = [x.strip() for x in cell.split(' / ')]
            if len(names) > 1:
                entries.append({'printed_column': col, 'rank': None, 'players': names, 'shared_listing': True,
                                'game_status': None, 'practice_status': None, 'match_status': 'Shared cell: no individual rank or status assigned'})
                continue
            name = names[0]
            injury = lookup.get((row['team'], norm(player_name(row['team'], name))))
            if injury is None:
                unmatched.append({'team': row['team'], 'player': name, 'depth_id': row['id']})
            entries.append({'printed_column': col, 'rank': col, 'players': [name], 'shared_listing': False,
                            'game_status': injury['game_status'] if injury else None,
                            'practice_status': injury['practice_status'] if injury else None,
                            'injury_source_id': 'A958-NFL-INJURIES' if injury else None,
                            'match_status': 'Exact normalized name' if injury else 'No matching injury row; availability unknown'})
        occupied = [e for e in entries if e]
        first = entries[0] if entries else None
        exposure = bool(first and first['game_status'] == 'Out')
        later_out = [e for e in occupied[1:] if e['game_status'] == 'Out']
        gaps = any(x is None for x in entries[:max((e['printed_column'] for e in occupied), default=0)])
        joined.append({**row, 'entries': entries, 'first_string_out': exposure,
                       'later_listed_out': [n for e in later_out for n in e['players']],
                       'decision_state': 'Starter Out — replacement not confirmed by chart' if exposure else 'Review practice limitation / uncertain status' if any(e['game_status'] in ('Questionable', 'Doubtful') or e['practice_status'] == PRACTICE['D'] for e in occupied) else 'No listed absence designation; not a health guarantee',
                       'blank_backup_columns': gaps,
                       'actual_replacement': None, 'performance_deficit': None,
                       'source_ids': row['source_ids'] + (['A958-NFL-INJURIES'] if any(e.get('injury_source_id') for e in occupied) else [])})
    return joined, unmatched


def summary(injuries, depth, unmatched):
    return {'injury_rows': len(injuries), 'teams_with_injury_rows': len({r['team'] for r in injuries}),
            'practice_counts': dict(Counter(r['practice_status'] for r in injuries)),
            'game_status_counts': dict(Counter(r['game_status'] or 'Blank' for r in injuries)),
            'depth_slots': len(depth), 'depth_teams': len({r['team'] for r in depth}),
            'offense_slots': sum(r['unit'] == 'Offense' for r in depth),
            'defense_slots': sum(r['unit'] == 'Defense' for r in depth),
            'special_teams_slots': sum(r['unit'] == 'Special Teams' for r in depth),
            'first_string_out_slots': sum(r['first_string_out'] for r in depth),
            'slots_with_later_out': sum(bool(r['later_listed_out']) for r in depth),
            'unmatched_depth_names': len({(u['team'], norm(u['player'])) for u in unmatched}),
            'unmatched_depth_entries': len(unmatched),
            'scope': 'Descriptive counts of the transcribed snapshot, not incidence, player health, team quality or betting probabilities. A player can occupy multiple slots; unmatched names are unique team/name pairs, entries count slot appearances.'}


def build():
    injury_text = (ROOT / 'data/injuries-source.md').read_text()
    depth_text = (ROOT / 'data/depth-source.txt').read_text()
    injuries = parse_injuries(injury_text)
    raw_depth = parse_depth(depth_text)
    depth, unmatched = join_depth(raw_depth, injuries)
    data = {'checked_on': '2026-11-12', 'season': 2026, 'week': 10,
            'source_sha256': {'injuries_transcription': hashlib.sha256(injury_text.encode()).hexdigest(),
                              'depth_transcription': hashlib.sha256(depth_text.encode()).hexdigest()},
            'injuries': injuries, 'depth': depth, 'unmatched': unmatched, 'summary': summary(injuries, depth, unmatched),
            'evidence_boundary': 'Normalized transcription compared with official rendered pages, not a raw HTTP archive. Mutable URLs may not retain this snapshot. No source publication timestamp is invented.'}
    return data


def write():
    data = build()
    (ROOT / 'data/availability.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    for key, fields in [('injuries', ['id','team','player','position','injury','practice_status','game_status','source_url']), ('depth', ['id','team','unit','position','slot','first','second','third','fourth','fifth','source_url'])]:
        out = io.StringIO(); writer = csv.writer(out, lineterminator='\n'); writer.writerow(fields)
        sources = load_sources()
        for r in data[key]:
            if key == 'injuries':
                values = [r.get(f) for f in fields[:-1]]
            else:
                values = [r['id'],r['team'],r['unit'],r['position'],r['slot'],*r['players']]
            writer.writerow([*values, sources[r['source_ids'][0]]['url']])
        (ROOT / ('data/' + key + '.csv')).write_text(out.getvalue())
    return data


if __name__ == '__main__':
    print(json.dumps(write()['summary'], indent=2))
