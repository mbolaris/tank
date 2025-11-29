/**
 * Audio manager for poker game sound effects
 */

class AudioManager {
    private audioContext: AudioContext | null = null;
    private enabled: boolean = true;
    private volume: number = 0.5;

    constructor() {
        // Initialize AudioContext on first user interaction
        if (typeof window !== 'undefined') {
            document.addEventListener('click', () => this.initAudioContext(), { once: true });
        }
    }

    private initAudioContext() {
        if (!this.audioContext) {
            // Support for older browsers with webkitAudioContext
            const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
            this.audioContext = new AudioContextClass();
        }
    }

    setEnabled(enabled: boolean) {
        this.enabled = enabled;
    }

    setVolume(volume: number) {
        this.volume = Math.max(0, Math.min(1, volume));
    }

    private playTone(frequency: number, duration: number, type: OscillatorType = 'sine', fadeOut: boolean = true) {
        if (!this.enabled || !this.audioContext) return;

        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.frequency.value = frequency;
        oscillator.type = type;

        gainNode.gain.value = this.volume;

        if (fadeOut) {
            gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
        }

        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }

    private playNoise(duration: number, filterFreq: number = 1000) {
        if (!this.enabled || !this.audioContext) return;

        const bufferSize = this.audioContext.sampleRate * duration;
        const buffer = this.audioContext.createBuffer(1, bufferSize, this.audioContext.sampleRate);
        const output = buffer.getChannelData(0);

        for (let i = 0; i < bufferSize; i++) {
            output[i] = Math.random() * 2 - 1;
        }

        const noise = this.audioContext.createBufferSource();
        noise.buffer = buffer;

        const filter = this.audioContext.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.value = filterFreq;

        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = this.volume * 0.3;
        gainNode.gain.setValueAtTime(this.volume * 0.3, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);

        noise.connect(filter);
        filter.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        noise.start(this.audioContext.currentTime);
        noise.stop(this.audioContext.currentTime + duration);
    }

    // Card dealing sound - soft whoosh
    playCardDeal() {
        this.playNoise(0.15, 2000);
        this.playTone(800, 0.1, 'sine');
    }

    // Card shuffle sound
    playCardShuffle() {
        this.playNoise(0.4, 3000);
    }

    // Chip betting sound - clink
    playChipBet() {
        this.playTone(1200, 0.08, 'triangle');
        setTimeout(() => this.playTone(1000, 0.06, 'triangle'), 30);
    }

    // Chip stack sound - multiple chips
    playChipStack() {
        for (let i = 0; i < 3; i++) {
            setTimeout(() => this.playTone(1100 + i * 100, 0.05, 'triangle'), i * 40);
        }
    }

    // Fold action - low tone
    playFold() {
        this.playTone(200, 0.3, 'sine');
    }

    // Check action - soft click
    playCheck() {
        this.playTone(600, 0.08, 'square');
    }

    // Call action - medium tone
    playCall() {
        this.playTone(800, 0.15, 'sine');
        this.playChipBet();
    }

    // Raise action - ascending tones
    playRaise() {
        this.playTone(600, 0.1, 'sine');
        setTimeout(() => this.playTone(800, 0.1, 'sine'), 80);
        setTimeout(() => this.playTone(1000, 0.15, 'sine'), 160);
        setTimeout(() => this.playChipStack(), 100);
    }

    // Win sound - celebratory
    playWin() {
        const notes = [523, 659, 784, 1047]; // C, E, G, C (major chord)
        notes.forEach((freq, i) => {
            setTimeout(() => this.playTone(freq, 0.4, 'sine'), i * 100);
        });
    }

    // Lose sound - descending
    playLose() {
        this.playTone(400, 0.3, 'sine');
        setTimeout(() => this.playTone(300, 0.4, 'sine'), 150);
    }

    // All-in sound - dramatic
    playAllIn() {
        this.playTone(1200, 0.2, 'sawtooth');
        setTimeout(() => this.playTone(1400, 0.3, 'sawtooth'), 100);
        setTimeout(() => this.playChipStack(), 150);
    }
}

export const audioManager = new AudioManager();
