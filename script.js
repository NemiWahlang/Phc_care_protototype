const messagesEl = document.getElementById("messages");
const form = document.getElementById("composer");
const input = document.getElementById("villageInput");
const phcListEl = document.getElementById("phcList");

function addMessage(text, sender) {
  const div = document.createElement("div");
  div.className = "msg " + sender;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const village = input.value.trim();
  if (!village) return;

  addMessage(village, "user");
  input.value = "";

  try {
    const res = await fetch("/api/status/" + encodeURIComponent(village));

    if (!res.ok) {
      const err = await res.json();
      addMessage(err.detail || "Could not find that village.", "bot");
      return;
    }

    const data = await res.json();
    if (data.status === "Active") {
      addMessage(data.doctor_name + " is checked in at " + data.village_name + " PHC.", "bot");
    } else {
      addMessage("No doctor is checked in at " + data.village_name + " PHC right now.", "bot");
    }
  } catch (err) {
    addMessage("Connection error. Is the server running?", "bot");
  }
});

async function loadPhcs() {
  try {
    const res = await fetch("/api/phcs");
    const phcs = await res.json();

    phcListEl.innerHTML = "";
    phcs.forEach((phc) => {
      const li = document.createElement("li");
      li.className = "phc-row";
      li.innerHTML =
        '<div class="phc-info">' +
        '<span class="phc-name">' + phc.village_name + "</span>" +
        '<span class="phc-district">' + phc.district + "</span>" +
        "</div>" +
        '<span class="pill ' + phc.status.toLowerCase() + '">' + phc.status + "</span>" +
        '<button class="toggle-btn" data-id="' + phc.phc_id + '" type="button">Toggle</button>';
      phcListEl.appendChild(li);
    });
  } catch (err) {
    phcListEl.innerHTML = "<li class='hint'>Could not load PHC list.</li>";
  }
}

phcListEl.addEventListener("click", async (event) => {
  if (!event.target.classList.contains("toggle-btn")) return;
  await fetch("/api/toggle/" + event.target.dataset.id, { method: "POST" });
  loadPhcs();
});

loadPhcs();
