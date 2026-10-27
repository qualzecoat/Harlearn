"""Model-node API-key handling (phase 2, corrected spec).

There is NO separate provider-connection entity. Provider settings live
INSIDE the Model node: {base_url, api_key, model, temperature}.

Storage rule (this is the security boundary, read it before touching):
- What the client sends: ``config.api_key`` in plaintext, ONLY when the
  user typed a new key in the inspector.
- What the database stores: ``config.api_key_enc`` (Fernet) plus
  ``config.api_key_masked`` (e.g. ``sk-…abcd``). Plaintext is NEVER stored.
- What the client receives: ``config.api_key`` is always ``""``,
  plus ``api_key_masked`` and ``api_key_set``. The inspector shows the
  masked value as placeholder text, never as the input value, so an
  unchanged key is never submitted back.
- On save, an empty/missing ``api_key`` means "keep the stored key":
  the old ``api_key_enc``/``api_key_masked`` are copied forward, never
  overwritten with a masked placeholder. To remove a key, delete and
  recreate the Model node. GraphVersion snapshots store the same
  encrypted form, never plaintext.
"""

from . import crypto


def stored_nodes(incoming, old_by_id=None):
    """Translate client-submitted nodes into the DB (stored) form."""
    old_by_id = old_by_id or {}
    out = []
    for node in incoming:
        cfg = dict(node.get("config") or {})
        if node.get("type") == "Model":
            incoming_key = cfg.pop("api_key", None)
            cfg.pop("api_key_enc", None)
            cfg.pop("api_key_masked", None)
            cfg.pop("api_key_set", None)
            old = old_by_id.get(node.get("id")) or {}
            old_cfg = old.get("config") or {}
            if incoming_key and str(incoming_key).strip():
                if old_cfg.get("api_key_masked") and incoming_key == old_cfg["api_key_masked"]:
                    # Defensive: a masked placeholder must never become the key.
                    cfg["api_key_enc"] = old_cfg.get("api_key_enc", "")
                    cfg["api_key_masked"] = old_cfg.get("api_key_masked", "")
                else:
                    cfg["api_key_enc"] = crypto.encrypt_api_key(str(incoming_key))
                    cfg["api_key_masked"] = crypto.mask_api_key(str(incoming_key))
            elif old_cfg.get("api_key_enc"):
                cfg["api_key_enc"] = old_cfg["api_key_enc"]
                cfg["api_key_masked"] = old_cfg.get("api_key_masked", "")
            else:
                cfg["api_key_enc"] = ""
                cfg["api_key_masked"] = ""
            cfg["api_key_set"] = bool(cfg["api_key_enc"])
        out.append(
            {
                "id": node.get("id"),
                "type": node.get("type"),
                "x": node.get("x", 0),
                "y": node.get("y", 0),
                "config": cfg,
                "disabled": bool(node.get("disabled", False)),
            }
        )
    return out


def served_nodes(stored):
    """Translate DB (stored) nodes into the client-safe form."""
    out = []
    for node in stored:
        cfg = dict(node.get("config") or {})
        if node.get("type") == "Model":
            enc = cfg.pop("api_key_enc", "")
            cfg["api_key"] = ""
            cfg["api_key_masked"] = cfg.get("api_key_masked", "")
            cfg["api_key_set"] = bool(enc)
        out.append(
            {
                "id": node.get("id"),
                "type": node.get("type"),
                "x": node.get("x", 0),
                "y": node.get("y", 0),
                "config": cfg,
                "disabled": bool(node.get("disabled", False)),
            }
        )
    return out
