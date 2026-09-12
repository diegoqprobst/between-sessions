from server.channels.twilio import parse_command

def test_pause_and_resume():
    assert parse_command("pausa") == ("pause", "")
    assert parse_command("Reanudar") == ("resume", "")

def test_exclude_signal():
    assert parse_command("no compartas sueño") == ("exclude", "sueño")

def test_plain_text_is_not_command():
    assert parse_command("hoy dormí fatal") is None
