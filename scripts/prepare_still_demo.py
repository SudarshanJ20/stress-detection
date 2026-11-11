"""Make an explicitly prerecorded, private observation demo from an existing consented video."""
import argparse
from pathlib import Path
import av
from stress_detection.manifest import fingerprint
from stress_detection.pilot_state import atomic
from stress_detection.validate_sample import require_ignored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require_ignored(args.output.parent)
    if args.output.exists() or args.output.suffix.lower() != '.mp4':
        parser.error('Choose a fresh ignored .mp4 output path.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source_proof = fingerprint(args.input, str(args.input.resolve()))
    receipt = args.output.with_suffix('.provenance.json')
    if receipt.exists(): parser.error('Provenance output exists; choose a fresh path.')
    meta = {'status': 'encoding', 'source': 'prerecorded', 'purpose': 'observation demo only; no anxiety inference',
            'input': source_proof, 'maximum_source_seconds': 35.3, 'output_width_height': None,
            'timing': 'encoded from source frame PTS; encoded-container timing is not independently captured camera/wrist ground truth'}
    atomic(receipt, meta)
    try:
        with av.open(str(args.input)) as source, av.open(str(args.output), 'w') as target:
            original = source.streams.video[0]
            stream = target.add_stream('libx264', rate=original.average_rate)
            scale = 512 / max(original.width, original.height)
            stream.width = max(2, 2 * round(original.width * scale / 2))
            stream.height = max(2, 2 * round(original.height * scale / 2))
            meta['output_width_height'] = [stream.width, stream.height]
            stream.pix_fmt = 'yuv420p'
            stream.options = {'preset': 'fast', 'crf': '23'}
            origin = None
            for frame in source.decode(video=0):
                if frame.time is None: raise ValueError('Source timing is unavailable.')
                if origin is None: origin = frame.time
                if float(frame.time - origin) > 35.3: break
                converted = frame.reformat(width=stream.width, height=stream.height, format='yuv420p')
                converted.pts = frame.pts; converted.time_base = frame.time_base
                for packet in stream.encode(converted): target.mux(packet)
            for packet in stream.encode(): target.mux(packet)
        if fingerprint(args.input, str(args.input.resolve())) != source_proof:
            raise ValueError('Source changed while encoding.')
        meta.update(status='completed', output=fingerprint(args.output, str(args.output.resolve())))
    except BaseException:
        meta['status'] = 'failed'; raise
    finally:
        atomic(receipt, meta)
    print('Private prerecorded observation demo prepared. Select it explicitly in the camera page; it is not live webcam data.')


if __name__ == '__main__': main()
