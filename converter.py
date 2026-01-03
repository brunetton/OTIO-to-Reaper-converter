#!python3
# -*- coding: utf-8 -*-


"""
Usage:
    {self_filename} <input> <output>
"""

import logging
from pathlib import Path

import opentimelineio as otio
from docopt import docopt

log = logging.getLogger(__name__)

def convert_otio_to_reaper(otio_file, output_rpp):
    timeline = otio.adapters.read_from_file(str(otio_file))

    rpp_lines = [
        "<REAPER_PROJECT 0.1 \"6.75/linux-x64\" 1683103437",
        "  <NOTES 0 0",
        "  >",
        "  GRID 3198 8 1 8 1 0 0 0",    # No grid displayed
        "  TIMEMODE 0 5 -1 30 0 0 -1",  # Timecode in time (not bars)
    ]

    track_number = 0
    for track_id, track in enumerate(timeline.tracks):
        if not isinstance(track, otio.schema.Track):
            continue
        if not track.kind in ('Audio', 'Video'):
            log.warning(f"Track #{track_id}: unsupported track type: \"{track.kind}\", ignoring entiere track")
        if track.kind == "Video":
            log.debug(f"Ignore video track: #{track_id}")
            continue
        if not track.has_clips():
            # filter out empty tracks
            continue

        track_number += 1
        log.debug(f"Track #{track_id}: #{track_number}")
        rpp_lines.append("  <TRACK")
        rpp_lines.append(f'    NAME "{track.name or 'A' + str(track_number)}"')

        for item in track:
            if isinstance(item, otio.schema.Clip):
                log.debug(f"  - Item: {item.name}")
                if type(item.media_reference) == otio.schema.MissingReference:
                    log.info(f"Warning: ignore item \"{item.name}\" on track #{track_id} as it has no reference to a media file")
                    continue

                # Convert times in seconds
                pos = item.range_in_parent().start_time.to_seconds()
                dur = item.duration().to_seconds()
                off = item.source_range.start_time.to_seconds()

                # Convert generic URLs to paths
                path = Path(item.media_reference.target_url)
                source_type = None
                url_path = path.suffix.lower()
                match url_path:
                    case ".mp4":
                        source_type = "VIDEO"
                    case ".mov":
                        source_type = "VIDEO"
                    case ".wav":
                        source_type = "WAV"
                    case _:
                        raise Exception(f"Unknow file extension: {url_path}")

                # Bloc ITEM en texte pur
                rpp_lines.append("    <ITEM")
                rpp_lines.append(f"      POSITION {pos}")
                rpp_lines.append(f"      LENGTH {dur}")
                rpp_lines.append(f"      SOFFS {off}")
                rpp_lines.append(f"      NAME {path.name}")
                rpp_lines.append(f"      <SOURCE {source_type}")
                if source_type == "VIDEO":
                    rpp_lines.append(f"        HIRESPEAKS 1")  # Ask Reaper to build hi-res peaks
                rpp_lines.append(f'        FILE "{path}"')
                rpp_lines.append("      >")
                rpp_lines.append("    >")

        rpp_lines.append("  >") # TRACK end

    rpp_lines.append(">") # PROJECT end

    # Final write
    with open(output_rpp, "w", encoding="utf-8") as f:
        f.write("\n".join(rpp_lines))


# Main
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
args = docopt(__doc__.format(self_filename=Path(__file__).name))

convert_otio_to_reaper(Path(args["<input>"]).expanduser(), Path(args["<output>"]).expanduser())
