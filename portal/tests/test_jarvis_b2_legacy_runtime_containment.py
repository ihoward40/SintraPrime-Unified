"""Runtime containment tests for present legacy mutation surfaces."""
import pytest

from portal.services.jarvis_legacy_containment import LEGACY_CONTAINMENT_MAP
from portal.services.jarvis_legacy_runtime_guard import guarded_legacy_mutation


@pytest.mark.parametrize("surface", [item for item in LEGACY_CONTAINMENT_MAP if item.mutation_capable])
def test_present_mutation_surface_denies_direct_invocation(surface):
    calls = []

    def mutation(**_kwargs):
        calls.append(True)

    with pytest.raises(PermissionError, match="LEGACY_BYPASS_DENIED"):
        guarded_legacy_mutation(surface=surface, governed_context=None, mutation=mutation)
    assert calls == []
