from nadmon.provenance import read_head_commit, run_metadata

SHA = "5a09fd6" + "0" * 33


def test_reads_commit_from_loose_branch_ref(tmp_path):
    (tmp_path / "refs" / "heads").mkdir(parents=True)
    (tmp_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (tmp_path / "refs" / "heads" / "main").write_text(SHA + "\n", encoding="utf-8")
    assert read_head_commit(tmp_path) == SHA


def test_reads_commit_from_packed_refs(tmp_path):
    (tmp_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (tmp_path / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\n" + f"{SHA} refs/heads/main\n",
        encoding="utf-8",
    )
    assert read_head_commit(tmp_path) == SHA


def test_reads_detached_head(tmp_path):
    (tmp_path / "HEAD").write_text(SHA + "\n", encoding="utf-8")
    assert read_head_commit(tmp_path) == SHA


def test_missing_git_folder_returns_none(tmp_path):
    assert read_head_commit(tmp_path / "nope") is None


def test_run_metadata_finds_commit_without_git_command(monkeypatch):
    monkeypatch.setattr("nadmon.provenance._git", lambda *args: None)
    meta = run_metadata()
    assert meta["git_commit"] is not None and len(meta["git_commit"]) == 40
    assert meta["git_uncommitted_changes"] is None
