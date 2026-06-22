### Added

- ui: each expanded shortlist row's **Tailored CV** and **Cover letter** pane now has a **Copy**
  button (right-aligned next to the title) that copies the raw Markdown source to the clipboard,
  with brief "Copied" feedback. The raw `cv`/`cover_letter` is carried in an esc'd `data-md`
  attribute; the click never toggles the row.
