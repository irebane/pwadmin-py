<?php
// Run from the pwadmin-py directory:
//   php scripts/convert_items.php > data/pw_items.json
$phpApp = dirname(__DIR__) . '/../pwadmin';
include $phpApp . '/php/pw_items.php';
if (file_exists($phpApp . '/php/pw_items_ext.php')) {
    include $phpApp . '/php/pw_items_ext.php';
}
echo json_encode($ItemMod, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
