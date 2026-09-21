(function () {
  document.querySelectorAll(".drop-zone").forEach((dropZone) => {
    const fileInput = dropZone.querySelector(".file-input");
    const browseButton = dropZone.querySelector(".browse-button");
    const dropFilename = dropZone.querySelector(".drop-filename");

    if (!fileInput) return;

    function showFilename() {
      if (fileInput.files.length > 0 && dropFilename) {
        dropFilename.textContent = fileInput.files[0].name;
      }
    }

    if (browseButton) {
      browseButton.addEventListener("click", () => fileInput.click());
    }
    fileInput.addEventListener("change", showFilename);

    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("dragover");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        fileInput.files = files;
        showFilename();
      }
    });
  });
})();

(function () {
  document.querySelectorAll(".item-edit-button").forEach((editButton) => {
    const form = document.getElementById(editButton.getAttribute("aria-controls"));
    const item = editButton.closest(".reorder-item");
    if (!form || !item) return;

    function setOpen(open) {
      form.hidden = !open;
      editButton.setAttribute("aria-expanded", String(open));
      item.draggable = !open;
      if (open) form.querySelector("input")?.focus();
    }

    editButton.addEventListener("click", () => {
      setOpen(editButton.getAttribute("aria-expanded") !== "true");
    });
    form.querySelector(".item-edit-cancel")?.addEventListener("click", () => {
      setOpen(false);
      editButton.focus();
    });
  });
})();

(function () {
  document.querySelectorAll("[data-reorder-url]").forEach((container) => {
    let draggedEl = null;

    function clearDragOver() {
      container
        .querySelectorAll(".reorder-item.drag-over")
        .forEach((el) => el.classList.remove("drag-over"));
    }

    function sendOrder() {
      const order = Array.from(container.querySelectorAll(".reorder-item")).map((el) =>
        parseInt(el.dataset.id, 10)
      );
      fetch(container.dataset.reorderUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order: order }),
      }).catch(() => location.reload());
    }

    container.addEventListener("dragstart", (e) => {
      const item = e.target.closest(".reorder-item");
      if (!item) return;
      draggedEl = item;
      item.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    container.addEventListener("dragend", (e) => {
      const item = e.target.closest(".reorder-item");
      if (item) item.classList.remove("dragging");
      clearDragOver();
      draggedEl = null;
    });

    container.addEventListener("dragover", (e) => {
      const item = e.target.closest(".reorder-item");
      if (!item || item === draggedEl) return;
      e.preventDefault();
      clearDragOver();
      item.classList.add("drag-over");
    });

    container.addEventListener("drop", (e) => {
      const target = e.target.closest(".reorder-item");
      if (!target || !draggedEl || target === draggedEl) return;
      e.preventDefault();
      clearDragOver();

      const items = Array.from(container.querySelectorAll(".reorder-item"));
      if (items.indexOf(draggedEl) < items.indexOf(target)) {
        target.after(draggedEl);
      } else {
        target.before(draggedEl);
      }

      sendOrder();
    });
  });
})();
