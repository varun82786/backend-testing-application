"""Centralised registry for bug injection flags.

The OMS embeds deliberate, configurable bugs for QA / testing purposes.
Each bug is controlled by an ``enable_<name>`` boolean in the
application ``Settings``.  ``BugRegistry`` provides a clean lookup
interface that keeps the rest of the codebase decoupled from the
settings structure.

Example::

    from app.bugs.registry import bug_registry

    if bug_registry.is_active("WRONG_GST"):
        # apply intentionally incorrect calculation
        ...
"""

from app.core.config import get_settings


class BugRegistry:
    """Read-only registry for checking whether a named bug is active.

    Bug names are upper-case identifiers that map to Settings fields::

        Bug name              Settings field
        ─────────────────── → ─────────────────────────────────
        NEGATIVE_INVENTORY    enable_negative_inventory
        DUPLICATE_PAYMENT     enable_duplicate_payment
        WRONG_GST             enable_wrong_gst
        SKIP_AUDIT_LOG        enable_skip_audit_log
        SHIPMENT_WITHOUT_PAYMENT  enable_shipment_without_payment
    """

    @staticmethod
    def is_active(bug_name: str) -> bool:
        """Check whether a bug injection flag is currently enabled.

        Args:
            bug_name: Upper-case bug identifier (e.g.
                ``"NEGATIVE_INVENTORY"``).

        Returns:
            ``True`` if the corresponding ``enable_*`` setting is
            truthy, ``False`` otherwise (including when the setting does
            not exist).
        """
        settings = get_settings()
        flag_name = f"enable_{bug_name.lower()}"
        return getattr(settings, flag_name, False)


# Module-level singleton for convenient imports.
bug_registry = BugRegistry()
