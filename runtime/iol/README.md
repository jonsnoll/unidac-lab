# IOL compatibility sandbox

This directory contains the isolated legacy userspace prepared
for the Cisco IOL runtime provider.

The Cisco executable is not copied into the container image.
It is mounted read-only only when a runtime instance needs it.

The analyzed IOL binary is a Linux i386 executable and requires
the legacy SONAME `libcrypto.so.4`.

The Ubuntu 24.04 WSL host is intentionally kept free of this
legacy compatibility layer.

## Legacy dependency strategy

The sandbox uses an i386 Ubuntu 14.04 base image.

It does not run `apt update` against Trusty repositories.

During the controlled build, the host downloads the exact
`libssl1.0.0` i386 package from Ubuntu old-releases, validates
its Debian package metadata, and places it temporarily in the
Docker build context.

The package is installed only inside the sandbox image. A
compatibility symlink exposes its `libcrypto.so.1.0.0` under
the SONAME expected by the analyzed IOL binary.

The temporary DEB is removed from the project after the build.

## Current scope

The sandbox currently performs dependency validation only.

It does not start Cisco IOL and it does not generate or bypass
IOL licensing.

A future provider will require a user-supplied, authorized
runtime configuration before an instance may be started.
