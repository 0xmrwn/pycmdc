from typer.testing import CliRunner

from cmdc import cli

runner = CliRunner()


def test_version_option():
    """
    Test that --version prints the banner and version information.
    """
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    # Verify that the banner ASCII art and version are in the output.
    assert "cmdc" in result.output
    assert "version" in result.output.lower()


def test_config_flag(monkeypatch):
    """
    Test that the --config flag delegates to ConfigManager.handle_config and exits.
    """
    from cmdc.config_manager import ConfigManager

    called = {"handle_config": False}

    def fake_handle_config(self, force):
        called["handle_config"] = True
        print("Fake config handled")

    monkeypatch.setattr(ConfigManager, "handle_config", fake_handle_config)
    result = runner.invoke(cli.app, ["--config"])
    assert called["handle_config"], "handle_config was not called"
    assert "Fake config handled" in result.output
    assert result.exit_code == 0


def test_config_show_flag(monkeypatch):
    """
    Test that --config-show prints the configuration.
    """
    from cmdc.config_manager import ConfigManager

    called = {"display_config": False}

    def fake_display_config(self):
        called["display_config"] = True
        print("Fake config displayed")

    monkeypatch.setattr(ConfigManager, "display_config", fake_display_config)
    result = runner.invoke(cli.app, ["--config-show"])
    assert called["display_config"], "display_config was not called"
    assert "Fake config displayed" in result.output
    assert result.exit_code == 0


def test_list_ignore_flag(monkeypatch):
    """
    Test that --list-ignore prints the ignore patterns.
    """
    from cmdc.config_manager import ConfigManager

    called = {"display_ignore_patterns": False}

    def fake_display_ignore_patterns(self):
        called["display_ignore_patterns"] = True
        print("Fake ignore patterns displayed")

    monkeypatch.setattr(
        ConfigManager, "display_ignore_patterns", fake_display_ignore_patterns
    )
    result = runner.invoke(cli.app, ["--list-ignore"])
    assert called["display_ignore_patterns"], "display_ignore_patterns was not called"
    assert "Fake ignore patterns displayed" in result.output
    assert result.exit_code == 0


def test_add_ignore_flag(monkeypatch):
    """
    Test that --add-ignore delegates to add_ignore_patterns with the proper arguments.
    Note: For list options, pass the flag multiple times.
    """
    from cmdc.config_manager import ConfigManager

    called = {"add_ignore_patterns": False}

    def fake_add_ignore_patterns(self, patterns):
        called["add_ignore_patterns"] = True
        print("Fake add ignore patterns: " + ", ".join(patterns))

    monkeypatch.setattr(ConfigManager, "add_ignore_patterns", fake_add_ignore_patterns)
    # Pass the flag twice so that the list gets populated.
    result = runner.invoke(cli.app, ["--add-ignore", "*.log", "--add-ignore", "temp/*"])
    assert called["add_ignore_patterns"], "add_ignore_patterns was not called"
    assert "Fake add ignore patterns" in result.output
    assert "*.log" in result.output
    assert "temp/*" in result.output
    assert result.exit_code == 0


def test_non_interactive_flow(monkeypatch, tmp_path):
    """
    Test a non-interactive run of the CLI.
    This test simulates a directory containing a dummy file and replaces the
    scan/select and output functions with fakes so that no interactive prompts occur.
    """
    from cmdc.file_browser import FileBrowser
    from cmdc.output_handler import OutputHandler

    # Set up a temporary directory with one dummy file.
    d = tmp_path / "dummy_dir"
    d.mkdir()
    dummy_file = d / "dummy.py"
    dummy_file.write_text("print('hello')")

    def fake_scan_and_select_files(self, non_interactive):
        return (["dummy.py"], 42)

    monkeypatch.setattr(
        FileBrowser, "scan_and_select_files", fake_scan_and_select_files
    )

    def fake_process_output(self, selected_files, output_mode):
        print("Fake output processed with selected files: " + ", ".join(selected_files))
        return (True, None)

    monkeypatch.setattr(OutputHandler, "process_output", fake_process_output)

    result = runner.invoke(
        cli.app, [str(d), "--non-interactive", "--output", "console"]
    )
    assert "Fake output processed with selected files: dummy.py" in result.output
    assert "Total tokens" in result.output
    assert result.exit_code == 0
