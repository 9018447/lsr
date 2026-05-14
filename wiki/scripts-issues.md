# scripts-issues

## Overview

Directory-based community: scripts

- **Size**: 74 nodes
- **Cohesion**: 0.0893
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| embed_font | Function | /home/smh/aider/scripts/30k-image.py | 26-43 |
| generate_confetti | Function | /home/smh/aider/scripts/30k-image.py | 46-130 |
| generate_celebration_svg | Function | /home/smh/aider/scripts/30k-image.py | 133-204 |
| blame | Function | /home/smh/aider/scripts/blame.py | 29-68 |
| get_all_commit_hashes_between_tags | Function | /home/smh/aider/scripts/blame.py | 71-79 |
| run | Function | /home/smh/aider/scripts/blame.py | 82-85 |
| get_commit_authors | Function | /home/smh/aider/scripts/blame.py | 88-101 |
| process_all_tags_since | Function | /home/smh/aider/scripts/blame.py | 107-134 |
| get_latest_version_tag | Function | /home/smh/aider/scripts/blame.py | 137-142 |
| main | Function | /home/smh/aider/scripts/blame.py | 145-222 |
| get_counts_for_file | Function | /home/smh/aider/scripts/blame.py | 225-276 |
| get_all_tags_since | Function | /home/smh/aider/scripts/blame.py | 279-287 |
| get_tag_date | Function | /home/smh/aider/scripts/blame.py | 290-292 |
| find_block_lines | Function | /home/smh/aider/scripts/clean_metadata.py | 11-91 |
| remove_block_surgically | Function | /home/smh/aider/scripts/clean_metadata.py | 94-122 |
| main | Function | /home/smh/aider/scripts/clean_metadata.py | 125-254 |
| download_icon | Function | /home/smh/aider/scripts/dl_icons.py | 28-44 |
| main | Function | /home/smh/aider/scripts/dl_icons.py | 47-55 |
| ensure_cache_dir | Function | /home/smh/aider/scripts/homepage.py | 30-32 |
| get_cache_path | Function | /home/smh/aider/scripts/homepage.py | 35-37 |
| read_from_cache | Function | /home/smh/aider/scripts/homepage.py | 40-64 |
| write_to_cache | Function | /home/smh/aider/scripts/homepage.py | 67-85 |
| get_downloads_from_bigquery | Function | /home/smh/aider/scripts/homepage.py | 88-150 |
| get_total_downloads | Function | /home/smh/aider/scripts/homepage.py | 153-185 |
| get_github_stars | Function | /home/smh/aider/scripts/homepage.py | 188-205 |
| get_latest_release_aider_percentage | Function | /home/smh/aider/scripts/homepage.py | 208-255 |
| format_number | Function | /home/smh/aider/scripts/homepage.py | 258-272 |
| generate_badges_md | Function | /home/smh/aider/scripts/homepage.py | 275-296 |
| get_badges_md | Function | /home/smh/aider/scripts/homepage.py | 299-335 |
| get_badges_html | Function | /home/smh/aider/scripts/homepage.py | 338-406 |
| get_testimonials_js | Function | /home/smh/aider/scripts/homepage.py | 409-523 |
| main | Function | /home/smh/aider/scripts/homepage.py | 526-611 |
| has_been_reopened | Function | /home/smh/aider/scripts/issues.py | 14-19 |
| get_issues | Function | /home/smh/aider/scripts/issues.py | 72-101 |
| group_issues_by_subject | Function | /home/smh/aider/scripts/issues.py | 104-111 |
| find_oldest_issue | Function | /home/smh/aider/scripts/issues.py | 114-125 |
| comment_and_close_duplicate | Function | /home/smh/aider/scripts/issues.py | 128-149 |
| find_unlabeled_with_paul_comments | Function | /home/smh/aider/scripts/issues.py | 152-171 |
| handle_unlabeled_issues | Function | /home/smh/aider/scripts/issues.py | 174-201 |
| handle_stale_issues | Function | /home/smh/aider/scripts/issues.py | 204-246 |
| handle_stale_closing | Function | /home/smh/aider/scripts/issues.py | 249-332 |
| handle_fixed_issues | Function | /home/smh/aider/scripts/issues.py | 335-394 |
| handle_duplicate_issues | Function | /home/smh/aider/scripts/issues.py | 397-434 |
| main | Function | /home/smh/aider/scripts/issues.py | 437-454 |
| subset_font | Function | /home/smh/aider/scripts/logo_svg.py | 16-54 |
| generate_svg_with_embedded_font | Function | /home/smh/aider/scripts/logo_svg.py | 57-119 |
| main | Function | /home/smh/aider/scripts/logo_svg.py | 122-170 |
| collect_model_stats | Function | /home/smh/aider/scripts/my_models.py | 8-30 |
| format_text_table | Function | /home/smh/aider/scripts/my_models.py | 33-50 |
| format_html_table | Function | /home/smh/aider/scripts/my_models.py | 53-93 |

*... and 24 more members.*

## Execution Flows

- **main** (criticality: 0.42, depth: 2)
- **get_badges_html** (criticality: 0.41, depth: 4)
- **main** (criticality: 0.41, depth: 4)
- **get_badges_md** (criticality: 0.41, depth: 4)
- **main** (criticality: 0.37, depth: 2)
- **handle_duplicate_issues** (criticality: 0.37, depth: 2)
- **main** (criticality: 0.37, depth: 2)
- **main** (criticality: 0.37, depth: 2)
- **generate_celebration_svg** (criticality: 0.36, depth: 1)
- **main** (criticality: 0.36, depth: 1)
- *... and 7 more flows.*

## Dependencies

### Outgoing

- `print` (168 edge(s))
- `get` (41 edge(s))
- `strip` (32 edge(s))
- `len` (32 edge(s))
- `open` (31 edge(s))
- `add_argument` (26 edge(s))
- `append` (22 edge(s))
- `split` (21 edge(s))
- `raise_for_status` (21 edge(s))
- `exists` (19 edge(s))
- `join` (18 edge(s))
- `run` (18 edge(s))
- `write` (16 edge(s))
- `lower` (15 edge(s))
- `startswith` (12 edge(s))

### Incoming

- `/home/smh/aider/scripts/homepage.py` (14 edge(s))
- `/home/smh/aider/scripts/issues.py` (12 edge(s))
- `/home/smh/aider/scripts/blame.py` (10 edge(s))
- `/home/smh/aider/scripts/recording_audio.py` (9 edge(s))
- `/home/smh/aider/scripts/versionbump.py` (5 edge(s))
- `/home/smh/aider/scripts/update-history.py` (4 edge(s))
- `/home/smh/aider/scripts/30k-image.py` (3 edge(s))
- `/home/smh/aider/scripts/clean_metadata.py` (3 edge(s))
- `/home/smh/aider/scripts/logo_svg.py` (3 edge(s))
- `/home/smh/aider/scripts/my_models.py` (3 edge(s))
- `/home/smh/aider/scripts/tsl_pack_langs.py` (3 edge(s))
- `/home/smh/aider/scripts/dl_icons.py` (2 edge(s))
- `/home/smh/aider/scripts/yank-old-versions.py` (2 edge(s))
- `/home/smh/aider/scripts/redact-cast.py` (1 edge(s))
