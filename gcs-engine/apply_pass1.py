from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass1.py <xray-engine-root>")

root = Path(sys.argv[1])
inv = root / "src/xrGame/ui/UIActorMenuInventory.cpp"
trade = root / "src/xrGame/ui/UIActorMenuTrade.cpp"


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
# Inventory action hot path: FindItemInList already returns the exact cell.
# Reusing that cell avoids immediately scanning the same potentially-large list
# a second time in RemoveItemFromList.
# -----------------------------------------------------------------------------
replace_exact(
    inv,
    "\treturn false;\n}\n\nbool RemoveItemFromList(CUIDragDropListEx* lst, PIItem pItem)\n",
    "\treturn false;\n}\n\n"
    "// GCS performance: callers that already paid the cost of FindItemInList should\n"
    "// not scan the same drag/drop list a second time just to remove the found cell.\n"
    "bool RemoveFoundItemFromList(CUIDragDropListEx* lst, CUICellItem* ci)\n"
    "{\n"
    "\tif (!ci)\n"
    "\t\treturn false;\n\n"
    "\tCUICellItem* dying_cell = lst->RemoveItem(ci, false);\n"
    "\txr_delete(dying_cell);\n"
    "\treturn true;\n"
    "}\n\n"
    "bool RemoveItemFromList(CUIDragDropListEx* lst, PIItem pItem)\n",
)

replace_exact(
    inv,
    "\tif (FindItemInList(lst, pItem, ci))\n"
    "\t{\n"
    "\t\tR_ASSERT(ci);\n\n"
    "\t\tCUICellItem* dying_cell = lst->RemoveItem(ci, false);\n"
    "\t\txr_delete(dying_cell);\n\n"
    "\t\treturn true;\n"
    "\t}\n",
    "\tif (FindItemInList(lst, pItem, ci))\n"
    "\t{\n"
    "\t\tR_ASSERT(ci);\n"
    "\t\treturn RemoveFoundItemFromList(lst, ci);\n"
    "\t}\n",
)

replace_exact(
    inv,
    "\t\t\t\tif (FindItemInList(curr, pItem, ci))\n"
    "\t\t\t\t{\n"
    "\t\t\t\t\tif (lst_to_add != curr)\n"
    "\t\t\t\t\t\tRemoveItemFromList(curr, pItem);\n",
    "\t\t\t\tif (FindItemInList(curr, pItem, ci))\n"
    "\t\t\t\t{\n"
    "\t\t\t\t\tif (lst_to_add != curr)\n"
    "\t\t\t\t\t\tRemoveFoundItemFromList(curr, ci);\n",
)

replace_exact(
    inv,
    "\t\t\t\t\tif (FindItemInList(curr, pItem, ci))\n"
    "\t\t\t\t\t{\n"
    "\t\t\t\t\t\tif (lst_to_add != curr)\n"
    "\t\t\t\t\t\t\tRemoveItemFromList(curr, pItem);\n",
    "\t\t\t\t\tif (FindItemInList(curr, pItem, ci))\n"
    "\t\t\t\t\t{\n"
    "\t\t\t\t\t\tif (lst_to_add != curr)\n"
    "\t\t\t\t\t\t\tRemoveFoundItemFromList(curr, ci);\n",
)

# -----------------------------------------------------------------------------
# Inventory filter hot path: parse the active category once per list rebuild,
# not once for every item in the ruck.
# -----------------------------------------------------------------------------
replace_exact(
    inv,
    "void CUIActorMenu::FilterActorBagList(int mode)\n"
    "{\n"
    "\tm_pInventoryBagList->ClearAll(true);\n\n"
    "\tCUIDragDropListEx* templist = NULL;\n\n"
    "\tTIItemContainer ruck_list;\n"
    "\truck_list = m_pActorInvOwner->inventory().m_ruck;\n"
    "\tstd::sort(ruck_list.begin(), ruck_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tTIItemContainer::iterator itb = ruck_list.begin();\n",
    "void CUIActorMenu::FilterActorBagList(int mode)\n"
    "{\n"
    "\tm_pInventoryBagList->ClearAll(true);\n\n"
    "\tCUIDragDropListEx* templist = NULL;\n\n"
    "\tTIItemContainer ruck_list;\n"
    "\truck_list = m_pActorInvOwner->inventory().m_ruck;\n"
    "\tstd::sort(ruck_list.begin(), ruck_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tconst bool show_all = (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"));\n"
    "\tconst int kinds = show_all ? 0 : _GetItemCount(m_sort_kinds[mode]);\n"
    "\tTIItemContainer::iterator itb = ruck_list.begin();\n",
)

replace_exact(
    inv,
    "\t\tPIItem iitm = *itb;\n"
    "\t\tint kinds = _GetItemCount(m_sort_kinds[mode]);\n\n"
    "\t\tif (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"))\n",
    "\t\tPIItem iitm = *itb;\n"
    "\t\tif (show_all)\n",
)

# -----------------------------------------------------------------------------
# Trader category filtering has the same repeated parsing pattern on both the
# actor and trader inventories. Hoist it out of both per-item loops.
# -----------------------------------------------------------------------------
replace_exact(
    trade,
    "void CUIActorMenu::FilterActorTradeBagList(int mode)\n"
    "{\n"
    "\tm_pTradeActorBagList->ClearAll(true);\n\n"
    "\tTIItemContainer ruck_list;\n"
    "\truck_list = m_pActorInvOwner->inventory().m_ruck;\n"
    "\tstd::sort(ruck_list.begin(), ruck_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tTIItemContainer::iterator itb = ruck_list.begin();\n",
    "void CUIActorMenu::FilterActorTradeBagList(int mode)\n"
    "{\n"
    "\tm_pTradeActorBagList->ClearAll(true);\n\n"
    "\tTIItemContainer ruck_list;\n"
    "\truck_list = m_pActorInvOwner->inventory().m_ruck;\n"
    "\tstd::sort(ruck_list.begin(), ruck_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tconst bool show_all = (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"));\n"
    "\tconst int kinds = show_all ? 0 : _GetItemCount(m_sort_kinds[mode]);\n"
    "\tTIItemContainer::iterator itb = ruck_list.begin();\n",
)

replace_exact(
    trade,
    "\t\t\tPIItem iitm = *itb;\n\n"
    "\t\t\tint kinds = _GetItemCount(m_sort_kinds[mode]);\n\n"
    "\t\t\tif (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"))\n",
    "\t\t\tPIItem iitm = *itb;\n\n"
    "\t\t\tif (show_all)\n",
)

replace_exact(
    trade,
    "void CUIActorMenu::FilterTraderList(int mode)\n"
    "{\n"
    "\tm_pTradePartnerBagList->ClearAll(true);\n\n"
    "\tTIItemContainer items_list;\n"
    "\tm_pPartnerInvOwner->inventory().AddAvailableItems(items_list, true);\n"
    "\tstd::sort(items_list.begin(), items_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tTIItemContainer::iterator itb = items_list.begin();\n",
    "void CUIActorMenu::FilterTraderList(int mode)\n"
    "{\n"
    "\tm_pTradePartnerBagList->ClearAll(true);\n\n"
    "\tTIItemContainer items_list;\n"
    "\tm_pPartnerInvOwner->inventory().AddAvailableItems(items_list, true);\n"
    "\tstd::sort(items_list.begin(), items_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tconst bool show_all = (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"));\n"
    "\tconst int kinds = show_all ? 0 : _GetItemCount(m_sort_kinds[mode]);\n"
    "\tTIItemContainer::iterator itb = items_list.begin();\n",
)

replace_exact(
    trade,
    "\t\t\tPIItem iitm = *itb;\n"
    "\t\t\tint kinds = _GetItemCount(m_sort_kinds[mode]);\n\n"
    "\t\t\tif (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"))\n",
    "\t\t\tPIItem iitm = *itb;\n"
    "\t\t\tif (show_all)\n",
)

print("GCS Pass 1 source transforms applied successfully.")
