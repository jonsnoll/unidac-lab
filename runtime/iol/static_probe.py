#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


KEYWORDS = (
    "iourc",
    "license",
    "licence",
    "netmap",
    "ethernet",
    "interface",
    "console",
    "serial",
    "socket",
    "udp",
    "tcp",
    "port",
    "slot",
    "hostid",
    "hostname",
    "application",
    "usage",
    "help",
    "memory",
    "ram",
    "nvram",
    "startup",
    "config",
)

MAX_MATCHES_PER_KEYWORD = 80


class ProbeError(RuntimeError):
    pass


def run(command):
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    if process.returncode != 0:
        raise ProbeError(
            (
                "Command failed: "
                + " ".join(command)
                + "\n"
                + process.stderr
            )
        )

    return process.stdout


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def normalize_line(line):
    return (
        line
        .replace("\x00", "")
        .strip()
    )


def keyword_matches(strings_output):
    lines = [
        normalize_line(line)
        for line
        in strings_output.splitlines()
    ]

    result = {}

    for keyword in KEYWORDS:
        pattern = re.compile(
            re.escape(keyword),
            re.IGNORECASE,
        )

        matches = []

        for line in lines:
            if not line:
                continue

            if pattern.search(line):
                if line not in matches:
                    matches.append(
                        line
                    )

            if (
                len(matches)
                >= MAX_MATCHES_PER_KEYWORD
            ):
                break

        if matches:
            result[keyword] = matches

    return result


def option_candidates(strings_output):
    candidates = []

    option_pattern = re.compile(
        r"(^|\s)-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*"
    )

    for raw in strings_output.splitlines():
        line = normalize_line(
            raw
        )

        if not line:
            continue

        lowered = line.lower()

        interesting = (
            "usage" in lowered
            or "option" in lowered
            or "argument" in lowered
            or "command" in lowered
            or option_pattern.search(line)
        )

        if (
            interesting
            and
            line not in candidates
        ):
            candidates.append(
                line
            )

        if len(candidates) >= 250:
            break

    return candidates


def env_candidates(strings_output):
    env_re = re.compile(
        r"\b[A-Z][A-Z0-9_]{3,}\b"
    )

    allow_keywords = (
        "IOU",
        "IOL",
        "NET",
        "HOST",
        "LIC",
        "CONSOLE",
        "PORT",
        "SOCKET",
    )

    result = []

    for raw in strings_output.splitlines():
        line = normalize_line(
            raw
        )

        for candidate in env_re.findall(
            line
        ):
            if not any(
                token in candidate
                for token in allow_keywords
            ):
                continue

            if candidate not in result:
                result.append(
                    candidate
                )

            if len(result) >= 100:
                return result

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        required=True,
    )

    parser.add_argument(
        "--expected-sha256",
        default=None,
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

    if (
        args.expected_sha256
        and
        digest != args.expected_sha256
    ):
        raise ProbeError(
            "SHA256 mismatch"
        )

    file_output = run(
        [
            "file",
            str(image),
        ]
    ).strip()

    if (
        "ELF 32-bit LSB executable"
        not in file_output
    ):
        raise ProbeError(
            "Unexpected executable type"
        )

    elf_header = run(
        [
            "readelf",
            "-h",
            str(image),
        ]
    )

    program_headers = run(
        [
            "readelf",
            "-l",
            str(image),
        ]
    )

    dynamic = run(
        [
            "readelf",
            "-d",
            str(image),
        ]
    )

    strings_output = run(
        [
            "strings",
            "-a",
            "-n",
            "5",
            str(image),
        ]
    )

    result = {
        "probe_type":
            "static-only",

        "ios_executed":
            False,

        "image": {
            "path":
                str(image),

            "size_bytes":
                image.stat().st_size,

            "sha256":
                digest,

            "file":
                file_output,
        },

        "elf": {
            "header":
                elf_header.splitlines(),

            "program_headers":
                program_headers.splitlines(),

            "dynamic":
                dynamic.splitlines(),
        },

        "keyword_matches":
            keyword_matches(
                strings_output
            ),

        "option_candidates":
            option_candidates(
                strings_output
            ),

        "environment_candidates":
            env_candidates(
                strings_output
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
