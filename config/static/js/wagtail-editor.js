(() => {
  const LAYOUT_KEY = "skinmenu-editor-layout";
  const LAYOUTS = ["split", "preview"];

  const body = document.body;
  if (!body || !body.classList.contains("editor-view")) return;

  const applyLayout = (layout) => {
    LAYOUTS.forEach((name) => body.classList.remove(`sm-editor-layout--${name}`));
    body.classList.add(`sm-editor-layout--${layout}`);

    const toggles = document.querySelectorAll('[data-skinmenu-editor-toggle] [data-layout]');
    toggles.forEach((btn) => {
      btn.setAttribute("aria-pressed", btn.dataset.layout === layout ? "true" : "false");
    });

    if (layout === "split" || layout === "preview") {
      ensurePreviewPanelOpen();
    }
  };

  const ensurePreviewPanelOpen = () => {
    const toggle = document.querySelector('[data-side-panel-toggle="preview"]');
    if (!toggle) return;
    if (toggle.getAttribute("aria-expanded") === "true") return;
    toggle.click();
  };

  const stored = localStorage.getItem(LAYOUT_KEY);
  const initialLayout = LAYOUTS.includes(stored) ? stored : "preview";
  applyLayout(initialLayout);

  document.querySelectorAll('[data-skinmenu-editor-toggle] [data-layout]').forEach((btn) => {
    btn.addEventListener("click", () => {
      const layout = btn.dataset.layout;
      localStorage.setItem(LAYOUT_KEY, layout);
      applyLayout(layout);
    });
  });

  const moduleToggle = document.querySelector('[data-skinmenu-modules-toggle]');
  if (moduleToggle) {
    moduleToggle.addEventListener("click", () => {
      const drawer = ensureModuleDrawer();
      drawer.classList.toggle("is-open");
      body.classList.toggle("sm-module-drawer-open", drawer.classList.contains("is-open"));
    });
  }

  const MODULES = [
    "Hero",
    "Treatments carousel",
    "Text + Image",
    "Reviews carousel",
    "CTA",
    "Treatment products",
    "Text section",
    "Key facts",
    "Steps",
    "FAQs",
    "Pull quote",
    "Image / Video",
    "Who we are",
    "Values grid",
    "Founder",
  ];

  const ensureModuleDrawer = () => {
    let drawer = document.querySelector(".sm-module-drawer");
    if (drawer) return drawer;

    drawer = document.createElement("div");
    drawer.className = "sm-module-drawer";
    drawer.innerHTML = `
      <div class="sm-module-drawer__overlay" data-skinmenu-modules-close></div>
      <div class="sm-module-drawer__panel">
        <div class="sm-module-drawer__header">
          <h2>Module library</h2>
          <button type="button" class="sm-module-drawer__close" data-skinmenu-modules-close>Close</button>
        </div>
        <p class="sm-module-drawer__hint">Pick a module to insert into the page.</p>
        <div class="sm-module-drawer__grid"></div>
      </div>
    `;
    document.body.appendChild(drawer);

    drawer.querySelectorAll('[data-skinmenu-modules-close]').forEach((btn) => {
      btn.addEventListener("click", () => {
        drawer.classList.remove("is-open");
        body.classList.remove("sm-module-drawer-open");
      });
    });

    const grid = drawer.querySelector(".sm-module-drawer__grid");
    MODULES.forEach((label) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sm-module-drawer__card";
      button.innerHTML = `<span>${label}</span>`;
      button.addEventListener("click", () => {
        insertModule(label);
      });
      grid.appendChild(button);
    });

    return drawer;
  };

  let activeStreamfield = null;

  const registerStreamfieldFocus = () => {
    document.addEventListener("focusin", (event) => {
      const container = event.target.closest("[data-streamfield-stream-container]");
      if (container) {
        activeStreamfield = container;
      }
    });

    document.addEventListener("click", (event) => {
      const container = event.target.closest("[data-streamfield-stream-container]");
      if (container) {
        activeStreamfield = container;
      }
    });
  };

  const findAddButton = () => {
    if (activeStreamfield) {
      const addButton = activeStreamfield.parentElement?.querySelector(".c-sf-add-button");
      if (addButton) return addButton;
    }
    return document.querySelector(".c-sf-add-button");
  };

  const waitForOption = (label, attempt = 0) => {
    const options = Array.from(document.querySelectorAll(".w-combobox__option"));
    const normalized = label.trim().toLowerCase();
    const match = options.find((option) => {
      const text = option.querySelector(".w-combobox__option-text")?.textContent || option.textContent || \"\";
      return text.trim().toLowerCase() === normalized;
    });

    if (match) {
      match.click();
      return;
    }

    if (attempt < 20) {
      window.setTimeout(() => waitForOption(label, attempt + 1), 50);
    } else {
      console.warn(`Module '${label}' not found in this streamfield.`);
    }
  };

  const insertModule = (label) => {
    const addButton = findAddButton();
    if (!addButton) return;

    addButton.click();
    waitForOption(label);
  };

  registerStreamfieldFocus();

  const handleTopbarActions = () => {
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-skinmenu-action]");
      if (!button) return;

      const action = button.dataset.skinmenuAction;
      if (action === "save") {
        const form = document.querySelector("#page-edit-form");
        if (form) form.requestSubmit();
      }

      if (action === "publish") {
        const publishButton = document.querySelector('button[name="action-publish"]');
        if (publishButton) publishButton.click();
      }

      if (action === "preview") {
        const previewUrl = button.getAttribute("data-preview-url");
        if (previewUrl) {
          window.open(previewUrl, "_blank", "noopener");
        }
      }
    });
  };

  handleTopbarActions();
})();
