"use client"

import { useState, useEffect } from "react"
import { Moon, Sun } from "lucide-react"

type ModeToggleProps = {
  labeled?: boolean
}

export function ModeToggle({ labeled = false }: ModeToggleProps) {
  const [theme, setTheme] = useState<"light" | "dark">("light")
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const savedTheme = localStorage.getItem("theme") as "light" | "dark" | null
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
    const initialTheme = savedTheme || (prefersDark ? "dark" : "light")
    setTheme(initialTheme)
    applyTheme(initialTheme)
  }, [])

  const applyTheme = (newTheme: "light" | "dark") => {
    const root = document.documentElement
    if (newTheme === "dark") {
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
    }
    localStorage.setItem("theme", newTheme)
  }

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light"
    setTheme(newTheme)
    applyTheme(newTheme)
  }

  if (!mounted) {
    return <div className={labeled ? "mode-toggle-button labeled" : "mode-toggle-button"} aria-hidden />
  }

  const label = theme === "light" ? "Dark mode" : "Light mode"

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={labeled ? "mode-toggle-button labeled" : "mode-toggle-button"}
      aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
    >
      {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
      {labeled ? <span>{label}</span> : null}
    </button>
  )
}
