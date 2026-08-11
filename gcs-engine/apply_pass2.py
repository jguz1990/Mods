from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass2.py <xray-engine-root>")

root = Path(sys.argv[1])
trade = root / "src/xrGame/ui/UIActorMenuTrade.cpp"
cells = root / "src/xrGame/ui/UICellCustomItems.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the optimization transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# -----------------------------------------------------------------------------
# Trader eligibility is evaluated once for every visible actor item while the
# trade UI is built. CInventory already maintains m_fTotalWeight and exposes it
# through TotalWeight(); CalcTotalWeight() walks every item to rebuild the same
# value. Avoid that O(actor_items * partner_items) repeated scan.
# -----------------------------------------------------------------------------
replace_exact(
    trade,
    "\tfloat partner_inv_weight = m_pPartnerInvOwner->inventory().CalcTotalWeight();\n",
    "\tfloat partner_inv_weight = m_pPartnerInvOwner->inventory().TotalWeight();\n",
)

# -----------------------------------------------------------------------------
# Every condition-bearing inventory cell currently loads/parses the exact same
# actor_menu_item.xml file in its constructor. Inventory/trader opens can create
# hundreds of cells at once. Keep one parsed XML document and reuse it.
# UI cell construction occurs serially on the UI/game thread, and CUIXmlInit
# reads the document without changing its contents.
# -----------------------------------------------------------------------------
replace_exact(
    cells,
    "namespace detail\n"
    "{\n",
    "namespace\n"
    "{\n"
    "\tCUIXml& ActorMenuItemXml()\n"
    "\t{\n"
    "\t\tstatic CUIXml xml;\n"
    "\t\tstatic bool loaded = false;\n"
    "\t\tif (!loaded)\n"
    "\t\t{\n"
    "\t\t\txml.Load(CONFIG_PATH, UI_PATH, \"actor_menu_item.xml\");\n"
    "\t\t\tloaded = true;\n"
    "\t\t}\n"
    "\t\treturn xml;\n"
    "\t}\n"
    "}\n\n"
    "namespace detail\n"
    "{\n",
)

replace_exact(
    cells,
    "\tif (condbar)\n"
    "\t{\n"
    "\t\tCUIXml uiXml;\n"
    "\t\tuiXml.Load(CONFIG_PATH, UI_PATH, \"actor_menu_item.xml\");\n"
    "\t\tCUIXmlInit::InitProgressBar(uiXml, condbar, 0, m_pConditionState);\n"
    "\t}\n",
    "\tif (condbar)\n"
    "\t{\n"
    "\t\tCUIXmlInit::InitProgressBar(ActorMenuItemXml(), condbar, 0, m_pConditionState);\n"
    "\t}\n",
)

print("GCS Pass 2 source transforms applied successfully.")
