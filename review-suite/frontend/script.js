const API_BASE_URL = "http://127.0.0.1:8000";

// Small toast helper
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ==================================================
// =============== RESUME EVALUATOR =================
// ==================================================

// Resume upload → send file to backend
document.getElementById("evaluator-resume-file")
  ?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const fd = new FormData();
    fd.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/api/upload-resume`, {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast(`✅ Resume processed (${data.chunks_added} chunks stored)`, "success");
      } else {
        showToast("❌ Resume upload failed", "error");
      }
    } catch (err) {
      showToast("⚠️ Error uploading resume: " + err.message, "error");
    }
  });

// Job Description upload → extract & analyze
document.getElementById("evaluator-jd-file")
  ?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const fd = new FormData();
    fd.append("file", file);

    try {
      // Extract JD text
      const res = await fetch(`${API_BASE_URL}/api/extract-text`, {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      if (data?.text) {
        showToast("✅ JD extracted, analyzing...", "success");

        // Send JD text to analyzer
        const res2 = await fetch(`${API_BASE_URL}/api/analyze-resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: data.text }),
        });
        const analysis = await res2.json();

        document.getElementById("evaluator-results").innerText =
          analysis.feedback || "⚠️ No feedback received";
      } else {
        showToast("❌ Could not extract JD text", "error");
      }
    } catch (err) {
      showToast("⚠️ Error handling JD: " + err.message, "error");
    }
  });

// Manual Analyze button (in case JD is pasted manually)
// Analyze button → use uploaded JD file
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("analyze-btn")
    ?.addEventListener("click", async () => {
      const jdFile = document.getElementById("evaluator-jd-file")?.files[0];
      if (!jdFile) {
        showToast("Please upload a Job Description first", "error");
        return;
      }

      try {
        // Extract JD text from uploaded file
        const fd = new FormData();
        fd.append("file", jdFile);
        const res = await fetch(`${API_BASE_URL}/api/extract-text`, {
          method: "POST",
          body: fd,
        });
        const data = await res.json();

        if (!data?.text) {
          showToast("❌ Could not extract JD text", "error");
          return;
        }

        // Analyze against uploaded resumes
        const res2 = await fetch(`${API_BASE_URL}/api/analyze-resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: data.text }),
        });
        const analysis = await res2.json();

        document.getElementById("evaluator-results").innerText =
          analysis.feedback || "⚠️ No feedback received";
      } catch (err) {
        showToast("⚠️ Error analyzing resume: " + err.message, "error");
      }
    });
});


// ==================================================
// ================= BULK RANKING ===================
// ==================================================

document.getElementById("ranking-btn")
  ?.addEventListener("click", async () => {
    const jdFile = document.getElementById("ranking-jd-file")?.files[0];
    const resumes = document.getElementById("ranking-resume-files")?.files;
    if (!jdFile || resumes.length === 0) {
      showToast("Please upload resumes and a job description", "error");
      return;
    }

    try {
      // Extract JD text
      const fdJD = new FormData();
      fdJD.append("file", jdFile);
      const jdRes = await fetch(`${API_BASE_URL}/api/extract-text`, { method: "POST", body: fdJD });
      const jdData = await jdRes.json();
      if (!jdData?.text) {
        showToast("JD extraction failed", "error");
        return;
      }

      // Upload all resumes
      for (const file of resumes) {
        const fd = new FormData();
        fd.append("file", file);
        await fetch(`${API_BASE_URL}/api/upload-resume`, { method: "POST", body: fd });
      }

      // Call analyzer with JD
      const res = await fetch(`${API_BASE_URL}/api/analyze-resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: jdData.text }),
      });
      const data = await res.json();

      document.getElementById("ranking-results").innerText =
        data.feedback || "No ranking available";
    } catch (err) {
      showToast("⚠️ Error in bulk ranking: " + err.message, "error");
    }
  });

// ==================================================
// ============ RESUME IMPROVEMENT ==================
// ==================================================

document.getElementById("improvement-btn")
  ?.addEventListener("click", async () => {
    const resumeFile = document.getElementById("improvement-resume-file")?.files[0];
    if (!resumeFile) {
      showToast("Please upload your resume", "error");
      return;
    }

    try {
      // Upload resume
      const fd = new FormData();
      fd.append("file", resumeFile);
      await fetch(`${API_BASE_URL}/api/upload-resume`, { method: "POST", body: fd });

      // Generate improvement suggestions (reuse analyzer with a "fake JD")
      const fakeJD = "Please evaluate this resume and provide improvement suggestions for better job matches.";
      const res = await fetch(`${API_BASE_URL}/api/analyze-resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: fakeJD }),
      });
      const data = await res.json();

      document.getElementById("improvement-results").innerText =
        data.feedback || "No suggestions available";
    } catch (err) {
      showToast("⚠️ Error in improvement: " + err.message, "error");
    }
  });
