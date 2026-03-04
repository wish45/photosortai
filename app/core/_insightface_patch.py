"""Patch problematic insightface internals before import.

insightface==0.7.3 bundles Cython extensions (mesh_core_cython, etc.)
for 3D face mesh rendering. These often fail to compile on macOS/ARM
and in certain pip environments. Since we only use FaceAnalysis for
detection + ArcFace embeddings, we mock out the broken modules.

Import this module BEFORE importing insightface.
"""

import sys
import types
import logging

logger = logging.getLogger(__name__)


def apply():
    """Install stub modules so insightface imports don't crash."""
    _stubs = [
        # face3d mesh Cython extension (the reported crash)
        "insightface.thirdparty.face3d",
        "insightface.thirdparty.face3d.mesh",
        "insightface.thirdparty.face3d.mesh.cython",
        "insightface.thirdparty.face3d.mesh.cython.mesh_core_cython",
        # face3d morphable model (sometimes imported transitively)
        "insightface.thirdparty.face3d.morphable_model",
        "insightface.thirdparty.face3d.morphable_model.morphabel_model",
    ]

    patched = []
    for mod_name in _stubs:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)
            patched.append(mod_name)

    if patched:
        logger.debug(f"Patched insightface stubs: {patched}")


# Auto-apply on import
apply()
