"""Tes daftar split (docs/split_list.tsv): bentuk, jumlah, dan tidak ada grup yang terbelah.

Berkas hanya berisi hash, label, nomor grup, dan bagian; tanpa isi email.
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest

JALUR = Path("docs/split_list.tsv")
KOLOM = ["content_hash", "label", "group_final", "split", "fold"]


@pytest.fixture(scope="module")
def baris():
    with JALUR.open(encoding="utf-8", newline="") as f:
        pembaca = csv.reader(f, delimiter="\t")
        kepala = next(pembaca)
        isi = list(pembaca)
    assert kepala == KOLOM
    return isi


def test_bentuk_dan_jumlah(baris):
    assert len(baris) == 9298
    assert all(len(b) == 5 for b in baris)
    hashes = [b[0] for b in baris]
    assert len(set(hashes)) == 9298
    assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in hashes)
    assert {b[1] for b in baris} == {"ham", "spam", "phishing"}
    assert all(b[2].isdigit() and b[4] in {"-1", "0", "1", "2", "3", "4"} for b in baris)
    assert len({b[2] for b in baris}) == 4741


def test_jumlah_train_test_per_kelas(baris):
    hitung = Counter((b[3], b[1]) for b in baris)
    assert hitung == Counter({("train", "ham"): 3288, ("train", "spam"): 1448, ("train", "phishing"): 2702,
                              ("test", "ham"): 822, ("test", "spam"): 362, ("test", "phishing"): 676})


def test_tidak_ada_grup_terbelah(baris):
    bagian, lipatan = defaultdict(set), defaultdict(set)
    for _, _, grup, split, fold in baris:
        bagian[grup].add(split)
        if split == "train":
            lipatan[grup].add(fold)
        else:
            assert fold == "-1"
    assert all(len(s) == 1 for s in bagian.values())
    assert all(len(s) == 1 for s in lipatan.values())
    assert {f for s in lipatan.values() for f in s} == {"0", "1", "2", "3", "4"}


def test_baris_terurut_menurut_hash(baris):
    hashes = [b[0] for b in baris]
    assert hashes == sorted(hashes)