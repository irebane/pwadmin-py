<?php
// Run from the pwadmin-py directory:
//   php scripts/convert_items.php > data/pw_items.json
//
// Reads pw_items.php from https://github.com/shadowvzs/pwAdmin (PHP admin panel for
// PWI 1.4.2) — expected checked out as a sibling directory named "pwadmin". See
// README.md's Credits section.
$phpApp = dirname(__DIR__) . '/../pwadmin';
include $phpApp . '/php/pw_items.php';
if (file_exists($phpApp . '/php/pw_items_ext.php')) {
    include $phpApp . '/php/pw_items_ext.php';
}
echo json_encode($ItemMod, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
