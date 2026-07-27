import { describe, it, expect } from "vitest"
import { cn } from "../utils"

describe("cn (classname merge utility)", () => {
  it("merges simple class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar")
  })

  it("filters out falsy values", () => {
    expect(cn("foo", false && "bar", undefined, null, "baz")).toBe("foo baz")
  })

  it("handles conditional classes", () => {
    const isActive = true
    expect(cn("base", isActive && "active")).toBe("base active")
  })

  it("resolves tailwind conflicts via twMerge", () => {
    // Later classes override earlier conflicting tailwind utilities
    expect(cn("px-4 py-2", "px-6")).toBe("py-2 px-6")
  })

  it("returns empty string for no inputs", () => {
    expect(cn()).toBe("")
  })

  it("handles single class", () => {
    expect(cn("only")).toBe("only")
  })
})
