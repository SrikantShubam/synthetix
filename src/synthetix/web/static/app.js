const progress = document.querySelector("#progress[data-run-id]");
if (progress) {
  const runId = progress.dataset.runId;
  if (runId !== "demo") {
    const events = new EventSource(`/runs/${runId}/events`);
    events.onmessage = ({ data }) => {
      const state = JSON.parse(data);
      document.querySelector("#run-status").textContent = state.status;
      document.querySelector("#completed").textContent = state.completed ?? 0;
      document.querySelector("#total").textContent = state.total ?? "—";
      document.querySelector("#cost").textContent = state.cost_usd ?? 0;
      const bar = progress.querySelector("progress");
      bar.max = state.total ?? 1;
      bar.value = state.completed ?? 0;
      if (state.status === "completed") {
        events.close();
        window.location.assign(`/runs/${runId}/results`);
      }
      if (["cancelled", "failed"].includes(state.status)) events.close();
    };
  }
}

