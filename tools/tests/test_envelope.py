"""Tests for player.envelope — ADSR envelope generator."""

from player.envelope import Envelope, AdsrPreset, Stage, ADSR_PRESETS


class TestEnvelope:
    def test_init_idle(self):
        env = Envelope()
        assert env.stage == Stage.IDLE
        assert env.level == 0

    def test_attack_ramps_up(self):
        env = Envelope()
        env.set_adsr(attack=100, decay=0, sustain=255, release=100)
        env.note_on(100)

        for _ in range(10):
            env.tick()
        assert 0 < env.level < 100

        for _ in range(100):
            env.tick()
        assert env.level == 100

    def test_instant_attack(self):
        env = Envelope()
        env.set_adsr(attack=0, decay=0, sustain=255, release=0)
        env.note_on(80)
        env.tick()
        assert env.level == 80

    def test_decay_to_sustain(self):
        env = Envelope()
        # sustain=128 -> 50% of peak
        env.set_adsr(attack=0, decay=100, sustain=128, release=100)
        env.note_on(100)

        for _ in range(110):
            env.tick()

        # 100 * 128 / 255 ≈ 50
        assert 45 <= env.level <= 55

    def test_release_ramps_down(self):
        env = Envelope()
        env.set_adsr(attack=0, decay=0, sustain=255, release=200)
        env.note_on(100)
        env.tick()
        assert env.level == 100

        env.note_off()
        for _ in range(50):
            env.tick()
        assert 0 < env.level < 100

        for _ in range(200):
            env.tick()
        assert env.level == 0

    def test_instant_release(self):
        env = Envelope()
        env.set_adsr(attack=0, decay=0, sustain=255, release=0)
        env.note_on(80)
        env.tick()
        env.note_off()
        env.tick()
        assert env.level == 0
        assert env.stage == Stage.IDLE

    def test_all_presets_valid(self):
        for preset in AdsrPreset:
            assert preset in ADSR_PRESETS
            params = ADSR_PRESETS[preset]
            assert len(params) == 4

    def test_preset_piano_fast_attack(self):
        env = Envelope()
        env.set_preset(AdsrPreset.PIANO)
        env.note_on(100)
        # Piano attack = 4 ticks
        for _ in range(10):
            env.tick()
        assert env.level > 80

    def test_note_off_from_idle_noop(self):
        env = Envelope()
        env.note_off()  # Should not crash
        assert env.stage == Stage.IDLE
