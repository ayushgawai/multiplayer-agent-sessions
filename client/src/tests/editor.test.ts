// @vitest-environment jsdom
import { Editor } from "@tiptap/core";
import { describe, expect, it } from "vitest";
import { createCollabDoc } from "../lib/crdt";
import { buildEditorOptions } from "../lib/editorConfig";
import { buildPresenceState, announce } from "../lib/presence";

function mount(role: "author" | "reviewer" | "observer"): { editor: Editor; destroy: () => void } {
  const collab = createCollabDoc({ env: { VITE_USE_MOCK: "true" }, sessionId: "s" });
  const presence = announce(collab.awareness, { participantId: "p_1", displayName: "Ada", role });
  const editor = new Editor({
    element: document.createElement("div"),
    ...buildEditorOptions(collab, presence, role),
  });
  return {
    editor,
    destroy: () => {
      editor.destroy();
      collab.destroy();
    },
  };
}

describe("editor options", () => {
  it("observer editor is not editable; author and reviewer are", () => {
    const observer = mount("observer");
    const author = mount("author");
    const reviewer = mount("reviewer");
    expect(observer.editor.isEditable).toBe(false);
    expect(author.editor.isEditable).toBe(true);
    expect(reviewer.editor.isEditable).toBe(true);
    observer.destroy();
    author.destroy();
    reviewer.destroy();
  });

  it("registers the cursor extension with the participant name and colour", () => {
    const { editor, destroy } = mount("author");
    const names = editor.extensionManager.extensions.map((e) => e.name);
    expect(names).toContain("collaborationCursor");
    const state = buildPresenceState({ participantId: "p_1", displayName: "Ada", role: "author" });
    expect(state.user.name).toBe("Ada");
    destroy();
  });
});
