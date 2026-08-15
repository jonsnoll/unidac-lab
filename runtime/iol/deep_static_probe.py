#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


USAGE_ANCHOR = (
    "Usage: <image> [options] <application id>"
)

ANCHORS = (
    "Usage: <image> [options] <application id>",
    "<application id>: instance identifier",
    "IOU Usage:",
    "NETMAP",
    "unable to open NETMAP",
    "No ports found - check NETMAP",
    "no ports found - is router",
    "iourc",
    "IOURC",
    "IOU License Error:",
    "Disable local console, use remote console",
    "Ignore the NETMAP file",
    "Ignore options from the IOURC file",
    "Size of nvram in Kb",
    "Number of Serial interfaces",
)

OPTION_RE = re.compile(
    r"^-[A-Za-z0-9]"
    r"(?:$|[\t =<\[])"
)


class ProbeError(RuntimeError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def run_strings(path):
    process = subprocess.run(
        [
            "strings",
            "-a",
            "-t",
            "x",
            "-n",
            "4",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    if process.returncode != 0:
        raise ProbeError(
            process.stderr.strip()
            or
            "strings failed"
        )

    result = []

    pattern = re.compile(
        r"^\s*([0-9a-fA-F]+)\s+(.*)$"
    )

    for raw in process.stdout.splitlines():
        match = pattern.match(
            raw
        )

        if not match:
            continue

        result.append(
            {
                "offset":
                    int(
                        match.group(1),
                        16,
                    ),

                "offset_hex":
                    "0x"
                    + match.group(1).lower(),

                "text":
                    match.group(2),
            }
        )

    return result


def context_window(
    entries,
    index,
    before=35,
    after=55,
):
    start = max(
        0,
        index - before,
    )

    end = min(
        len(entries),
        index + after + 1,
    )

    return entries[
        start:end
    ]


def anchor_contexts(entries):
    results = []

    seen = set()

    for anchor in ANCHORS:
        indexes = [
            index
            for index, item
            in enumerate(entries)
            if anchor.lower()
            in item["text"].lower()
        ]

        for index in indexes[:3]:
            item = entries[
                index
            ]

            key = (
                anchor,
                item["offset"],
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            results.append(
                {
                    "anchor":
                        anchor,

                    "match":
                        item,

                    "window":
                        context_window(
                            entries,
                            index,
                        ),
                }
            )

    return results


def global_options(entries):
    options = []

    seen = set()

    for item in entries:
        text = (
            item["text"]
            .strip()
        )

        if not OPTION_RE.match(
            text
        ):
            continue

        if text in seen:
            continue

        # Reduz falsos positivos binarios.
        printable_ratio = (
            sum(
                32 <= ord(ch) <= 126
                for ch in text
            )
            / max(
                len(text),
                1,
            )
        )

        if printable_ratio < 0.95:
            continue

        if len(text) > 180:
            continue

        seen.add(
            text
        )

        options.append(
            {
                "offset":
                    item[
                        "offset"
                    ],

                "offset_hex":
                    item[
                        "offset_hex"
                    ],

                "text":
                    text,
            }
        )

    return options


def usage_cluster(entries):
    indexes = [
        index
        for index, item
        in enumerate(entries)
        if USAGE_ANCHOR.lower()
        in item["text"].lower()
    ]

    if not indexes:
        raise ProbeError(
            "Usage anchor not found"
        )

    index = indexes[0]

    # Janela maior porque a tabela de opcoes costuma
    # ficar fisicamente proxima do Usage em .rodata.
    return context_window(
        entries,
        index,
        before=80,
        after=180,
    )


def nearby_candidate_lines(cluster):
    keywords = (
        "default",
        "interface",
        "ethernet",
        "serial",
        "console",
        "netmap",
        "iourc",
        "memory",
        "ram",
        "nvram",
        "application",
        "instance",
        "remote",
        "ignore",
        "usage",
        "help",
        "port",
    )

    result = []

    for item in cluster:
        text = (
            item["text"]
            .strip()
        )

        lowered = (
            text.lower()
        )

        if (
            OPTION_RE.match(
                text
            )
            or any(
                keyword in lowered
                for keyword in keywords
            )
        ):
            result.append(
                item
            )

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        required=True,
    )

    parser.add_argument(
        "--expected-sha256",
        required=True,
    )

    args = parser.parse_args()

    image = Path(
        args.image
    ).resolve()

    if not image.is_file():
        raise ProbeError(
            f"Image not found: {image}"
        )

    digest = sha256_file(
        image
    )

    if digest != args.expected_sha256:
        raise ProbeError(
            "SHA256 mismatch"
        )

    entries = run_strings(
        image
    )

    cluster = usage_cluster(
        entries
    )

    result = {
        "probe_type":
            "deep-static-only",

        "ios_executed":
            False,

        "image": {
            "path":
                str(image),

            "size_bytes":
                image.stat().st_size,

            "sha256":
                digest,
        },

        "usage_cluster":
            cluster,

        "usage_candidates":
            nearby_candidate_lines(
                cluster
            ),

        "global_option_candidates":
            global_options(
                entries
            ),

        "anchor_contexts":
            anchor_contexts(
                entries
            ),
    }

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()

    except ProbeError as error:
        print(
            json.dumps(
                {
                    "status":
                        "error",

                    "message":
                        str(error),
                },
                indent=2,
            ),
            file=sys.stderr,
        )

        raise SystemExit(1)
