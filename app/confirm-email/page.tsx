"use client"

import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "next/navigation"

const apiBaseUrl = () => (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "")

export default function ConfirmEmailPage() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")

  const [status, setStatus] = useState<"idle" | "missing" | "loading" | "success" | "error">(
    "idle",
  )
  const [message, setMessage] = useState<string>("")

  const confirmEndpoint = useMemo(
    () => `${apiBaseUrl()}/api/accounts/accounts/confirm-email/`,
    [],
  )

  useEffect(() => {
    if (!token) {
      setStatus("missing")
      setMessage("Token não fornecido na URL.")
      return
    }

    const controller = new AbortController()

    async function confirmEmail() {
      setStatus("loading")
      try {
        const response = await fetch(confirmEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
          signal: controller.signal,
        })

        const payload = await response.json().catch(() => null)

        if (response.ok) {
          setStatus("success")
          setMessage(payload?.detail ?? "Email confirmado com sucesso.")
          return
        }

        setStatus("error")
        setMessage(payload?.detail ?? "Não foi possível confirmar o e-mail.")
      } catch (error) {
        if (controller.signal.aborted) return
        setStatus("error")
        setMessage("Não foi possível contactar o servidor. Tente novamente.")
      }
    }

    confirmEmail()

    return () => controller.abort()
  }, [confirmEndpoint, token])

  const statusLabel = {
    idle: "Aguardando confirmação…",
    missing: "Token ausente.",
    loading: "Confirmando email…",
    success: "Email confirmado!",
    error: "Erro ao confirmar.",
  }[status]

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12 text-slate-900">
      <div className="w-full max-w-xl rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <div className="mb-6 flex items-center gap-3">
          <span
            className={`h-3 w-3 rounded-full ${
              status === "success"
                ? "bg-emerald-500"
                : status === "error"
                  ? "bg-rose-500"
                  : status === "missing"
                    ? "bg-amber-500"
                    : "bg-slate-400"
            }`}
            aria-hidden
          />
          <div>
            <h1 className="text-xl font-semibold">Confirmação de e-mail</h1>
            <p className="text-sm text-slate-500">{statusLabel}</p>
          </div>
        </div>

        <div className="space-y-3 text-base leading-relaxed text-slate-700">
          {status === "loading" && <p>Estamos validando seu token…</p>}
          {status === "missing" && (
            <p>
              O link está incompleto. Verifique se você copiou todo o endereço enviado no
              e-mail de confirmação.
            </p>
          )}
          {status === "success" && (
            <p>
              {message} Agora você pode fechar esta aba e iniciar sessão com sua conta
              normalmente.
            </p>
          )}
          {status === "error" && (
            <p>
              {message} Se o problema persistir, solicite um novo e-mail de confirmação
              na página de login.
            </p>
          )}
          {status === "idle" && <p>Preparando ambiente para confirmar seu endereço…</p>}
        </div>

        {token && (
          <div className="mt-6 rounded-lg bg-slate-50 px-4 py-3 text-xs text-slate-500">
            <p className="font-semibold text-slate-600">Token recebido</p>
            <code className="break-all text-slate-700">{token}</code>
          </div>
        )}
      </div>
    </main>
  )
}
