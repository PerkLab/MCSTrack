#!/bin/bash
install -d "${ROOTFS_DIR}/home/admin/MCSTrack/"
cp -r "${STAGE_DIR}/../../../data" "${ROOTFS_DIR}/home/admin/MCSTrack/"
cp -r "${STAGE_DIR}/../../../src" "${ROOTFS_DIR}/home/admin/MCSTrack/"
cp "${STAGE_DIR}/../../../pyproject.toml" "${ROOTFS_DIR}/home/admin/MCSTrack/"
install -d "${ROOTFS_DIR}/usr/local/bin/"
install "${STAGE_DIR}/00_custom/files/mixer_startup" "${ROOTFS_DIR}/usr/local/bin/"
chmod +x "${ROOTFS_DIR}/usr/local/bin/mixer_startup"
