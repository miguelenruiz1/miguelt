import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Mail, ChevronLeft } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { userApi } from '@/lib/user-api'

const schema = z.object({
  email: z.string().email('Email inválido'),
})

type FormData = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: (email: string) => userApi.auth.forgotPassword(email),
    onSuccess: () => setSent(true),
  })

  const onSubmit = (data: FormData) => mutation.mutate(data.email)

  return (
    <div className="relative bg-white">
      <div className="relative flex flex-col justify-center w-full min-h-screen lg:h-screen lg:flex-row">
        {/* Left — form */}
        <div className="flex flex-col flex-1 px-5 sm:px-6 lg:px-0">
          <div className="w-full max-w-md pt-8 sm:pt-10 mx-auto">
            <Link
              to="/login"
              className="inline-flex items-center text-sm text-gray-500 transition-colors hover:text-gray-700"
            >
              <ChevronLeft className="h-5 w-5" />
              Volver al login
            </Link>
          </div>

          <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
            <div>
              {sent ? (
                <div className="text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 mx-auto mb-5">
                    <Mail className="h-7 w-7 text-primary" />
                  </div>
                  <h1 className="mb-2 text-2xl font-semibold text-gray-800 sm:text-3xl">
                    Revisa tu correo
                  </h1>
                  <p className="text-sm text-gray-500 mb-8 max-w-xs mx-auto">
                    Si el correo existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña.
                  </p>
                  <Link
                    to="/login"
                    className="inline-flex items-center justify-center rounded-lg bg-primary px-6 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-primary"
                  >
                    Volver al login
                  </Link>
                </div>
              ) : (
                <>
                  <div className="mb-5 sm:mb-8">
                    <h1 className="mb-2 text-2xl font-semibold text-gray-800 sm:text-3xl">
                      ¿Olvidaste tu contraseña?
                    </h1>
                    <p className="text-sm text-gray-500">
                      Ingresa tu email y te enviaremos un enlace para restablecerla.
                    </p>
                  </div>

                  <form onSubmit={handleSubmit(onSubmit)}>
                    <div className="space-y-6">
                      <div>
                        <label className="mb-1.5 block text-sm font-medium text-gray-700">
                          Email <span className="text-red-500">*</span>
                        </label>
                        <input
                          {...register('email')}
                          type="email"
                          autoComplete="email"
                          placeholder="tu@email.com"
                          className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm placeholder:text-gray-400 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
                        />
                        {errors.email && <p className="mt-1.5 text-xs text-red-500">{errors.email.message}</p>}
                      </div>

                      {mutation.error && (
                        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                          {mutation.error.message}
                        </div>
                      )}

                      <div>
                        <button
                          type="submit"
                          disabled={mutation.isPending}
                          className="flex w-full items-center justify-center rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {mutation.isPending ? 'Enviando...' : 'Enviar enlace'}
                        </button>
                      </div>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right — branded panel */}
        <div className="items-center hidden w-full h-full lg:w-1/2 bg-gray-900 lg:grid">
          <div className="relative flex items-center justify-center z-[1]">
            <div className="absolute right-0 top-0 -z-[1] w-full max-w-[250px] xl:max-w-[450px] opacity-20">
              <svg viewBox="0 0 405 405" fill="none" xmlns="http://www.w3.org/2000/svg">
                <g opacity="0.5">
                  {Array.from({ length: 16 }, (_, r) =>
                    Array.from({ length: 16 }, (_, c) => (
                      <rect key={`${r}-${c}`} x={c * 27} y={r * 27} width="2" height="2" rx="1" fill="white" fillOpacity="0.3" />
                    ))
                  ).flat()}
                </g>
              </svg>
            </div>
            <div className="absolute bottom-0 left-0 -z-[1] w-full max-w-[250px] xl:max-w-[450px] rotate-180 opacity-20">
              <svg viewBox="0 0 405 405" fill="none" xmlns="http://www.w3.org/2000/svg">
                <g opacity="0.5">
                  {Array.from({ length: 16 }, (_, r) =>
                    Array.from({ length: 16 }, (_, c) => (
                      <rect key={`${r}-${c}`} x={c * 27} y={r * 27} width="2" height="2" rx="1" fill="white" fillOpacity="0.3" />
                    ))
                  ).flat()}
                </g>
              </svg>
            </div>
            <div className="flex flex-col items-center max-w-xs">
              <svg width="56" height="56" viewBox="0 0 34 34" fill="none" className="mb-6">
                <rect width="34" height="34" rx="8" fill="#6366f1" />
                <path d="M8 11h18v2.5H18.5V25H15V13.5H8V11Z" fill="white" />
                <path d="M20 17h2.5v5.5H27V25H20V17Z" fill="white" opacity="0.7" />
              </svg>
              <h2 className="text-2xl font-bold text-white mb-3">
                Trace<span className="font-medium text-primary/50">Log</span>
              </h2>
              <p className="text-center text-gray-400">
                Recupera el acceso a tu cuenta de forma segura.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
