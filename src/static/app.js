"use strict";
// Semua teks ditampilkan lewat textContent (tidak pernah sebagai HTML). Tautan di dalam teks tidak dibuka.
const LABEL = {
  HIGH: ["RISIKO TINGGI", "Skor di atas ambang resmi model."],
  MEDIUM: [
    "PERLU DIPERIKSA",
    "Skor di antara batas bawah dan ambang resmi. Ini bukan berarti kemungkinan phishing.",
  ],
  LOW: ["RISIKO RENDAH", "Skor rendah menurut model. Ini bukan jaminan."],
  "TIDAK DAPAT DINILAI": [
    "TIDAK DAPAT DINILAI",
    "Model tidak punya dasar untuk menilai teks ini. Periksa manual.",
  ],
};
const CONTOH = {
  E09: "Contoh penipuan fiktif berbahasa Inggris (bukan email sungguhan).",
  E08: "Contoh sah fiktif bergaya kantor. Pada pengujian 9-4 pitanya MEDIUM: 'perlu diperiksa' bukan 'kemungkinan phishing'.",
  E11: "Contoh keterbatasan: email sah fiktif bertema bank dan akun. Pada pengujian 9-4 model memberi skor tinggi.",
};

function el(tag, teks, kelas) {
  const e = document.createElement(tag);
  if (teks !== undefined) e.textContent = teks;
  if (kelas) e.className = kelas;
  return e;
}

function daftarKata(judul, kata) {
  const kotak = el("div", undefined, "kata");
  kotak.append(el("h3", judul));
  if (kata.length === 0) {
    kotak.append(el("p", "Tidak ada.", "kecil"));
    return kotak;
  }
  const ul = el("ul");
  kata.forEach(function (d) {
    ul.append(
      el(
        "li",
        d.kata + " (" + (d.nilai > 0 ? "+" : "") + d.nilai.toFixed(3) + ")",
      ),
    );
  });
  kotak.append(ul);
  return kotak;
}

function tampil(h) {
  const hasil = document.getElementById("hasil");
  hasil.replaceChildren();
  const info = LABEL[h.status];
  const kartu = el(
    "div",
    undefined,
    "kartu status-" + h.status.replace(/ /g, "-"),
  );
  kartu.append(el("h2", info[0]), el("p", info[1]));
  if (h.lolos_gerbang) {
    kartu.append(
      el(
        "p",
        "Skor phishing (skor model, bukan probabilitas): " +
          h.p.phishing.toFixed(2),
      ),
    );
    kartu.append(
      el(
        "p",
        "Skor ham " +
          h.p.ham.toFixed(2) +
          ", spam " +
          h.p.spam.toFixed(2) +
          ", phishing " +
          h.p.phishing.toFixed(2) +
          ". Putusan model: " +
          h.putusan_model +
          ".",
      ),
    );
  } else {
    kartu.append(
      el(
        "p",
        "Hanya " +
          h.n_kenal +
          " dari " +
          h.n_token +
          " kata yang dikenal model (cakupan " +
          Math.round(h.cakupan * 100) +
          "%). Teks terlalu pendek, kosong, atau bukan bahasa Inggris. Skor tidak ditampilkan karena tidak bermakna.",
      ),
    );
  }
  kartu.append(
    el("p", h.n_link + " tautan terdeteksi di teks (tidak dibuka)."),
  );
  kartu.append(
    el(
      "p",
      h.kata_mendesak.length > 0
        ? "Kata mendesak (heuristik, daftar manual, tidak tervalidasi): " +
            h.kata_mendesak.join(", ") +
            "."
        : "Tidak ada kata mendesak dari daftar manual (daftar itu tidak tervalidasi).",
    ),
  );
  hasil.append(kartu);
  if (h.lolos_gerbang) {
    const kata = el("div", undefined, "kartu");
    kata.append(
      el(
        "p",
        "Kata yang paling menaikkan atau menurunkan skor menurut model. Ini bobot statistik, bukan penjelasan sebab-akibat.",
        "kecil",
      ),
    );
    kata.append(
      daftarKata("Menaikkan skor", h.kontribusi.pendorong),
      daftarKata("Menurunkan skor", h.kontribusi.menjauhi),
    );
    hasil.append(kata);
  }
  hasil.append(el("p", h.catatan, "kecil"));
}

function galat(pesan) {
  const hasil = document.getElementById("hasil");
  hasil.replaceChildren(el("p", "Galat: " + pesan, "galat"));
}

async function analisis() {
  const tombol = document.getElementById("analisis");
  tombol.disabled = true;
  try {
    const r = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ teks: document.getElementById("teks").value }),
    });
    const h = await r.json();
    if (!r.ok) throw new Error(h.error || "kode " + r.status);
    tampil(h);
  } catch (e) {
    galat(e.message);
  } finally {
    tombol.disabled = false;
  }
}

async function muatContoh(id) {
  try {
    const r = await fetch("/samples");
    const c = (await r.json()).find(function (x) {
      return x.id === id;
    });
    if (!c) throw new Error("contoh tidak ditemukan");
    document.getElementById("teks").value = c.teks;
    document.getElementById("info-contoh").textContent = CONTOH[id];
    document.getElementById("hasil").replaceChildren();
  } catch (e) {
    galat(e.message);
  }
}

document.getElementById("analisis").addEventListener("click", analisis);
document.querySelectorAll(".contoh").forEach(function (b) {
  b.addEventListener("click", function () {
    muatContoh(b.dataset.id);
  });
});
