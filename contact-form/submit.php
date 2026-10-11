<?php
// submissions ko CSV file me save karta hai
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: index.html');
    exit;
}

$name    = trim($_POST['name'] ?? '');
$phone   = trim($_POST['phone'] ?? '');
$message = trim($_POST['message'] ?? '');

if ($name === '' || $phone === '' || $message === '') {
    die('Saare fields bharna zaroori hai. <a href="index.html">Wapas jayein</a>');
}

$file = __DIR__ . '/submissions.csv';
$new  = !file_exists($file);

$fp = fopen($file, 'a');
if ($new) {
    fputcsv($fp, ['Date', 'Name', 'Phone', 'Message']);
}
fputcsv($fp, [date('Y-m-d H:i:s'), $name, $phone, $message]);
fclose($fp);
?>
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dhanyavaad!</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif}
body{background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#111;border:1px solid #222;border-radius:12px;padding:40px;text-align:center;max-width:400px}
.tick{font-size:56px;margin-bottom:16px}
h1{color:#39FF14;margin-bottom:8px}
p{color:#888;margin-bottom:20px}
a{color:#39FF14;text-decoration:none}
</style>
</head>
<body>
<div class="card">
<div class="tick">✅</div>
<h1>Dhanyavaad!</h1>
<p>Aapki details mil gayi hain. Hum jald sampark karenge.</p>
<a href="index.html">← Wapas jayein</a>
</div>
</body>
</html>
