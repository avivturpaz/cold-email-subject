const form = document.getElementById("subject-form");
const statusEl = document.getElementById("form-status");
const resultsList = document.getElementById("results-list");
const resultsEmpty = document.getElementById("results-empty");
const bestOpenPill = document.getElementById("best-open-pill");
const sampleButton = document.getElementById("fill-sample");

const sampleSubjects = [
  "Quick question about {{first_name}}",
  "Worth a look for {{company}}?",
  "A faster way to handle this",
  "Last chance to lock in this week",
  "Thought this might help your team",
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderResult(result, isBest) {
  const notes = result.notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("");
  const lengthWidth = Math.min(100, result.length_score);
  const personalizationWidth = Math.min(100, result.personalization_score);
  const urgencyWidth = Math.min(100, result.urgency_score);
  const spamWidth = Math.min(100, result.spam_risk);

  return `
    <article class="result-item ${isBest ? "best-card" : ""}">
      <div class="result-top">
        <div>
          <h3 class="result-title">Variant ${result.index}</h3>
          <div class="result-subject">${escapeHtml(result.subject)}</div>
        </div>
        <div class="result-badge">${result.predicted_open_rate}% open rate</div>
      </div>
      <div class="score-grid">
        <div class="score">
          <div class="score-label">Length</div>
          <div class="score-value">${result.length_score}</div>
          <div class="score-bar"><span style="width:${lengthWidth}%"></span></div>
        </div>
        <div class="score">
          <div class="score-label">Personalization</div>
          <div class="score-value">${result.personalization_score}</div>
          <div class="score-bar"><span style="width:${personalizationWidth}%"></span></div>
        </div>
        <div class="score">
          <div class="score-label">Urgency</div>
          <div class="score-value">${result.urgency_score}</div>
          <div class="score-bar"><span style="width:${urgencyWidth}%"></span></div>
        </div>
        <div class="score">
          <div class="score-label">Spam risk</div>
          <div class="score-value">${result.spam_risk}</div>
          <div class="score-bar bad"><span style="width:${spamWidth}%"></span></div>
        </div>
      </div>
      <ul class="notes">${notes}</ul>
    </article>
  `;
}

function getSubjects() {
  return Array.from(form.querySelectorAll("input[name^='subject_']")).map((input) => input.value.trim());
}

function setSubjects(subjects) {
  Array.from(form.querySelectorAll("input[name^='subject_']")).forEach((input, index) => {
    input.value = subjects[index] || "";
  });
}

sampleButton?.addEventListener("click", () => {
  setSubjects(sampleSubjects);
  statusEl.textContent = "Sample set loaded. Edit it and run the test.";
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const subjects = getSubjects();
  statusEl.textContent = "Scoring subject lines...";
  bestOpenPill.textContent = "Analyzing...";

  try {
    const response = await fetch("/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ subjects }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Unable to score subjects.");
    }

    const analysis = data.analysis;
    resultsEmpty.hidden = true;
    resultsList.hidden = false;
    resultsList.innerHTML = analysis.results
      .map((result) => renderResult(result, result.index === analysis.best_index))
      .join("");

    bestOpenPill.textContent = `${analysis.best_open_rate}% best open rate`;
    statusEl.textContent = `Saved test #${data.submission_id}. Best variant: ${analysis.best_subject}`;
    document.getElementById("results-list")?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    bestOpenPill.textContent = "No test yet";
    statusEl.textContent = error.message || "Something went wrong.";
  }
});
