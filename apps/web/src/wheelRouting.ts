// Let nested textareas/panels scroll natively, including at their boundaries.
// The bounded ancestor prevents wheel input leaking into canvas zoom.
export function overScrollablePanel(target: EventTarget | null): boolean {
  let element = target instanceof Element ? target : null;
  while (element) {
    const style = getComputedStyle(element);
    if (
      (/(auto|scroll)/.test(style.overflowY) &&
        element.scrollHeight > element.clientHeight) ||
      (/(auto|scroll)/.test(style.overflowX) &&
        element.scrollWidth > element.clientWidth)
    )
      return true;
    element = element.parentElement;
  }
  return false;
}
