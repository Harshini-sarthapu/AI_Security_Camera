/**
 * AI-POWERED SMART SECURITY CAMERA - DASHBOARD CONTROLLER
 * Real-time stats polling, alert notification, audio synthesizer,
 * snapshot modals, and camera hardware controls.
 */

// ============================================================
// AUDIO ALERT SYNTHESIZER (Web Audio API - No external files needed)
// ============================================================
class SoundAlertSystem {
    constructor() {
        this.audioCtx = null;
        this.enabled = true;
    }

    init() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.audioCtx = new AudioContext();
            }
        }
        if (this.audioCtx && this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
    }

    playBeep(riskLevel = "HIGH") {
        if (!this.enabled) return;
        try {
            this.init();
            if (!this.audioCtx) return;

            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);

            const now = this.audioCtx.currentTime;

            if (riskLevel === "HIGH") {
                // High alert alarm siren: 880Hz -> 440Hz -> 880Hz
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(880, now);
                osc.frequency.exponentialRampToValueAtTime(440, now + 0.15);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.3);

                gain.gain.setValueAtTime(0.3, now);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.45);

                osc.start(now);
                osc.stop(now + 0.45);
            } else {
                // Medium warning chime: 600Hz
                osc.type = "sine";
                osc.frequency.setValueAtTime(587.33, now);
                osc.frequency.setValueAtTime(880, now + 0.1);

                gain.gain.setValueAtTime(0.2, now);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);

                osc.start(now);
                osc.stop(now + 0.3);
            }
        } catch (e) {
            console.warn("Audio play blocked or unavailable:", e);
        }
    }
}

const soundSystem = new SoundAlertSystem();

// Enable audio on first user interaction anywhere
document.addEventListener("click", () => {
    soundSystem.init();
}, { once: true });

// ============================================================
// DASHBOARD POLLER & CONTROLLER
// ============================================================
let lastKnownEventId = 0;
let isPolling = true;

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initial fetches
    fetchStats();
    fetchRecentEvents();

    // 2. Start polling every 1200ms for smooth live updates
    setInterval(() => {
        if (isPolling) {
            fetchStats();
            fetchRecentEvents();
        }
    }, 1200);

    // 3. Bind camera control buttons
    const btnStart = document.getElementById("btn-start-camera");
    const btnStop = document.getElementById("btn-stop-camera");
    const btnUpload = document.getElementById("btn-upload-video");
    const fileInput = document.getElementById("video-file-input");

    if (btnStart) {
        btnStart.addEventListener("click", startCamera);
    }
    if (btnStop) {
        btnStop.addEventListener("click", stopCamera);
    }
    if (btnUpload && fileInput) {
        btnUpload.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", handleVideoUpload);
    }

    // 4. Bind sound toggle if present
    const soundToggle = document.getElementById("sound-toggle");
    if (soundToggle) {
        soundToggle.addEventListener("change", (e) => {
            soundSystem.enabled = e.target.checked;
        });
    }
});

// ============================================================
// API CALLS
// ============================================================

async function fetchStats() {
    try {
        const res = await fetch("/api/stats");
        if (!res.ok) return;
        const data = await res.json();

        // Update statistics cards
        const elCameraStatus = document.getElementById("stat-camera-status");
        const elPeopleCount = document.getElementById("stat-people-count");
        const elObjectCount = document.getElementById("stat-object-count");
        const elAlertCount = document.getElementById("stat-alert-count");
        const elModeBadge = document.getElementById("stream-mode-badge");

        if (elCameraStatus) elCameraStatus.textContent = data.camera_status || "ONLINE";
        if (elPeopleCount) elPeopleCount.textContent = data.people_detected || 0;
        if (elObjectCount) elObjectCount.textContent = data.objects_detected || 0;
        if (elAlertCount) elAlertCount.textContent = data.active_alerts_count || 0;

        if (elModeBadge) {
            elModeBadge.textContent = data.is_demo ? "DEMO VIDEO" : "LIVE CAMERA";
            elModeBadge.className = "mode-badge " + (data.is_demo ? "mode-demo" : "mode-live");
        }

        // Render current alerts list
        if (data.active_alerts) {
            renderActiveAlerts(data.active_alerts);
        }

    } catch (err) {
        console.warn("Error fetching stats:", err);
    }
}

async function fetchRecentEvents() {
    try {
        const res = await fetch("/api/events?limit=10");
        if (!res.ok) return;
        const events = await res.json();

        // Check if there are newly generated events to sound the alarm
        if (events.length > 0) {
            const newest = events[0];
            if (lastKnownEventId !== 0 && newest.id > lastKnownEventId) {
                // New event detected!
                soundSystem.playBeep(newest.risk_level);
            }
            lastKnownEventId = newest.id;
        }

        renderRecentEventsTable(events);
    } catch (err) {
        console.warn("Error fetching recent events:", err);
    }
}

function renderActiveAlerts(alerts) {
    const container = document.getElementById("alerts-container");
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <div class="empty-alerts">
                <div class="empty-alerts-icon">🛡️</div>
                <div style="font-weight: 600; color: var(--text-main);">No Active Alerts</div>
                <div style="font-size: 0.8rem; margin-top: 4px;">Surveillance sector is secure and nominal.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = alerts.map(a => `
        <div class="alert-item ${a.risk_level}">
            ${a.image_url ? `
                <img src="${a.image_url}" alt="Snapshot" class="alert-thumb" onclick="openSnapshotModal('${a.image_url}', '${a.event_type}', '${a.risk_level}', '${a.timestamp}', '${a.description.replace(/'/g, "\\'")}')" />
            ` : `
                <div class="alert-thumb" style="display:flex;align-items:center;justify-content:center;font-size:24px;">📷</div>
            `}
            <div class="alert-details">
                <div class="alert-top">
                    <span class="alert-type">${a.event_type}</span>
                    <span class="risk-badge ${a.risk_level}">${a.risk_level} RISK</span>
                </div>
                <div class="alert-meta">${a.camera || 'Camera 1'} &bull; ${a.location || 'Main'}</div>
                <div class="alert-desc">${a.description}</div>
                <div class="alert-time">${a.timestamp}</div>
            </div>
        </div>
    `).join("");
}

function renderRecentEventsTable(events) {
    const tbody = document.getElementById("recent-events-body");
    if (!tbody) return;

    if (!events || events.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--text-dim); padding: 30px;">
                    No security events recorded yet.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = events.map(e => `
        <tr>
            <td class="mono-cell">#${e.id}</td>
            <td style="font-weight: 600; color: #fff;">${e.event_type}</td>
            <td class="mono-cell">${e.timestamp}</td>
            <td>${e.camera || 'Camera 1'}</td>
            <td><span class="risk-badge ${e.risk_level}">${e.risk_level}</span></td>
            <td><span style="color: var(--status-online); font-size: 0.8rem;">● LOGGED</span></td>
            <td>
                ${e.image_path ? `
                    <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.78rem;" 
                        onclick="openSnapshotModal('/static/${e.image_path}', '${e.event_type}', '${e.risk_level}', '${e.timestamp}', '${(e.description || '').replace(/'/g, "\\'")}')">
                        👁 View
                    </button>
                ` : `<span style="color: var(--text-dim);">-</span>`}
            </td>
        </tr>
    `).join("");
}

// ============================================================
// CAMERA CONTROLS
// ============================================================

async function startCamera() {
    try {
        const res = await fetch("/start-camera", { method: "POST" });
        const data = await res.json();
        if (data.status === "ok") {
            reloadVideoFeed();
            fetchStats();
        } else {
            alert(data.message || "Could not start camera");
        }
    } catch (e) {
        alert("Error connecting to camera server: " + e.message);
    }
}

async function stopCamera() {
    try {
        const res = await fetch("/stop-camera", { method: "POST" });
        const data = await res.json();
        if (data.status === "ok") {
            const feedImg = document.getElementById("video-feed-img");
            if (feedImg) {
                feedImg.src = "";
            }
            fetchStats();
        }
    } catch (e) {
        alert("Error stopping camera: " + e.message);
    }
}

function reloadVideoFeed() {
    const feedImg = document.getElementById("video-feed-img");
    if (feedImg) {
        feedImg.src = "/video-feed?t=" + new Date().getTime();
    }
}

async function handleVideoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("video", file);

    const btnUpload = document.getElementById("btn-upload-video");
    const originalText = btnUpload ? btnUpload.innerHTML : "";
    if (btnUpload) btnUpload.innerHTML = "⏳ Uploading...";

    try {
        const res = await fetch("/upload-video", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "ok") {
            reloadVideoFeed();
            fetchStats();
            alert("Demo video uploaded successfully! Running detection on video feed.");
        } else {
            alert(data.message || "Failed to upload video");
        }
    } catch (e) {
        alert("Upload error: " + e.message);
    } finally {
        if (btnUpload) btnUpload.innerHTML = originalText;
    }
}

// ============================================================
// SNAPSHOT MODAL
// ============================================================
function openSnapshotModal(imgSrc, eventType, riskLevel, timestamp, desc) {
    const modal = document.getElementById("snapshot-modal");
    const modalImg = document.getElementById("modal-snapshot-img");
    const modalTitle = document.getElementById("modal-title");
    const modalMeta = document.getElementById("modal-meta");

    if (!modal) return;

    if (modalImg) modalImg.src = imgSrc;
    if (modalTitle) modalTitle.textContent = `${eventType} Snapshot`;
    if (modalMeta) {
        modalMeta.innerHTML = `
            <div><strong>Risk:</strong> <span class="risk-badge ${riskLevel}">${riskLevel}</span></div>
            <div><strong>Time:</strong> ${timestamp}</div>
            <div><strong>Details:</strong> ${desc}</div>
        `;
    }

    modal.classList.add("active");
}

function closeSnapshotModal() {
    const modal = document.getElementById("snapshot-modal");
    if (modal) modal.classList.remove("active");
}

// Global hook for modal closing
window.closeSnapshotModal = closeSnapshotModal;
window.openSnapshotModal = openSnapshotModal;
