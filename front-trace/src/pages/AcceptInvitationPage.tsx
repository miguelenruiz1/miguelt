import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Check, Eye, EyeOff, ChevronLeft } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { userApi } from '@/lib/user-api'

const schema = z
  .object({
    password: z.string().min(8, 'Mínimo 8 caracteres'),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  })

type FormData = z.infer<typeof schema>

const inputClass =
  'h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-foreground  placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20'

function BrandPanel() {
  return (
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
          <p className="text-center text-muted-foreground">
            Has sido invitado a unirte. Establece tu contraseña para activar tu cuenta.
          </p>
        </div>
      </div>
    </div>
  )
}

export function AcceptInvitationPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const [success, setSuccess] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: (data: { token: string; password: string }) =>
      userApi.auth.acceptInvitation(data),
    onSuccess: () => setSuccess(true),
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({ token, password: data.password })
  }

  if (!token) {
    return (
      <div className="relative p-6 bg-card sm:p-0">
        <div className="relative flex flex-col justify-center w-full h-screen lg:flex-row sm:p-0">
          <div className="flex flex-col flex-1">
            <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto text-center">
              <p className="text-red-600 font-medium mb-4">Token de invitación no encontrado.</p>
              <Link to="/login" className="text-primary hover:text-primary text-sm font-medium">
                Ir al login
              </Link>
            </div>
          </div>
          <BrandPanel />
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="relative p-6 bg-card sm:p-0">
        <div className="relative flex flex-col justify-center w-full h-screen lg:flex-row sm:p-0">
          <div className="flex flex-col flex-1">
            <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 mx-auto mb-5">
                <Check className="h-7 w-7 text-emerald-600" />
              </div>
              <h1 className="mb-2 text-2xl font-semibold text-foreground">Cuenta activada</h1>
              <p className="text-sm text-muted-foreground mb-8">Tu contraseña ha sido establecida. Ya puedes iniciar sesión.</p>
              <button
                onClick={() => navigate('/login')}
                className="flex w-full items-center justify-center rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white  transition hover:bg-primary"
              >
                Ir al login
              </button>
            </div>
          </div>
          <BrandPanel />
        </div>
      </div>
    )
  }

  return (
    <div className="relative bg-card">
      <div className="relative flex flex-col justify-center w-full min-h-screen lg:h-screen lg:flex-row">
        {/* Left — form */}
        <div className="flex flex-col flex-1 px-5 sm:px-6 lg:px-0">
          <div className="w-full max-w-md pt-8 sm:pt-10 mx-auto">
            <Link
              to="/login"
              className="inline-flex items-center text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <ChevronLeft className="h-5 w-5" />
              Volver al login
            </Link>
          </div>

          <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
            <div>
              <div className="mb-5 sm:mb-8">
                <h1 className="mb-2 text-2xl font-semibold text-foreground sm:text-3xl">
                  Activa tu cuenta
                </h1>
                <p className="text-sm text-muted-foreground">
                  Establece una contraseña para completar tu registro
                </p>
              </div>

              <form onSubmit={handleSubmit(onSubmit)}>
                <div className="space-y-6">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-foreground">
                      Contraseña <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <input
                        {...register('password')}
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        className={inputClass}
                        placeholder="Mínimo 8 caracteres"
                      />
                      <span
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                      >
                        {showPassword ? (
                          <Eye className="h-5 w-5 text-muted-foreground" />
                        ) : (
                          <EyeOff className="h-5 w-5 text-muted-foreground" />
                        )}
                      </span>
                    </div>
                    {errors.password && <p className="mt-1.5 text-xs text-red-500">{errors.password.message}</p>}
                  </div>

                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-foreground">
                      Confirmar contraseña <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <input
                        {...register('confirmPassword')}
                        type={showConfirm ? 'text' : 'password'}
                        autoComplete="new-password"
                        className={inputClass}
                        placeholder="Repite tu contraseña"
                      />
                      <span
                        onClick={() => setShowConfirm(!showConfirm)}
                        className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                      >
                        {showConfirm ? (
                          <Eye className="h-5 w-5 text-muted-foreground" />
                        ) : (
                          <EyeOff className="h-5 w-5 text-muted-foreground" />
                        )}
                      </span>
                    </div>
                    {errors.confirmPassword && <p className="mt-1.5 text-xs text-red-500">{errors.confirmPassword.message}</p>}
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
                      className="flex w-full items-center justify-center rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white  transition hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {mutation.isPending ? 'Activando...' : 'Activar cuenta'}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* Right — branded panel */}
        <BrandPanel />
      </div>
    </div>
  )
}
