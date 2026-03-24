import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Mail, Phone, Building2, Briefcase, Globe, Languages, Camera, Trash2, Loader2, Pencil } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { useUpdateProfile, useChangePassword, useUploadAvatar, useDeleteAvatar } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const profileSchema = z.object({
  full_name: z.string().min(1, 'Nombre requerido'),
  username: z.string().min(3, 'Mínimo 3 caracteres'),
  email: z.string().email('Email inválido'),
  phone: z.string().max(30).optional().or(z.literal('')),
  job_title: z.string().max(255).optional().or(z.literal('')),
  company: z.string().max(255).optional().or(z.literal('')),
  bio: z.string().max(500).optional().or(z.literal('')),
  timezone: z.string().optional().or(z.literal('')),
  language: z.string().optional().or(z.literal('')),
})

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Requerido'),
    new_password: z.string().min(8, 'Mínimo 8 caracteres'),
    confirm_password: z.string().min(1, 'Confirma la contraseña'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Las contraseñas no coinciden',
    path: ['confirm_password'],
  })

type ProfileData = z.infer<typeof profileSchema>
type PasswordData = z.infer<typeof passwordSchema>

const TIMEZONES = [
  'America/Bogota',
  'America/Mexico_City',
  'America/Lima',
  'America/Santiago',
  'America/Buenos_Aires',
  'America/Sao_Paulo',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/Madrid',
  'Europe/London',
  'UTC',
]

const LANGUAGES = [
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' },
  { value: 'pt', label: 'Português' },
]

const USER_API_BASE = import.meta.env.VITE_USER_API_URL ?? 'http://localhost:9001'

const inputCls = 'w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-all hover:border-slate-300'
const labelCls = 'block text-sm font-medium text-slate-700 mb-1.5'

export function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const updateProfile = useUpdateProfile()
  const changePassword = useChangePassword()
  const uploadAvatar = useUploadAvatar()
  const deleteAvatar = useDeleteAvatar()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false)

  const profileForm = useForm<ProfileData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name ?? '',
      username: user?.username ?? '',
      email: user?.email ?? '',
      phone: user?.phone ?? '',
      job_title: user?.job_title ?? '',
      company: user?.company ?? '',
      bio: user?.bio ?? '',
      timezone: user?.timezone ?? 'America/Bogota',
      language: user?.language ?? 'es',
    },
  })

  const passwordForm = useForm<PasswordData>({
    resolver: zodResolver(passwordSchema),
  })

  if (!user) return null

  const initial = user.full_name?.[0]?.toUpperCase() ?? '?'
  const avatarSrc = user.avatar_url
    ? (user.avatar_url.startsWith('http') ? user.avatar_url : `${USER_API_BASE}${user.avatar_url}`)
    : null

  const handleProfileSubmit = (data: ProfileData) => {
    const payload: Record<string, string> = {}
    if (data.full_name !== user.full_name) payload.full_name = data.full_name
    if (data.username !== user.username) payload.username = data.username
    if (data.email !== user.email) payload.email = data.email
    if ((data.phone ?? '') !== (user.phone ?? '')) payload.phone = data.phone || ''
    if ((data.job_title ?? '') !== (user.job_title ?? '')) payload.job_title = data.job_title || ''
    if ((data.company ?? '') !== (user.company ?? '')) payload.company = data.company || ''
    if ((data.bio ?? '') !== (user.bio ?? '')) payload.bio = data.bio || ''
    if ((data.timezone ?? '') !== (user.timezone ?? '')) payload.timezone = data.timezone || ''
    if ((data.language ?? '') !== (user.language ?? '')) payload.language = data.language || ''

    if (Object.keys(payload).length > 0) {
      updateProfile.mutate(payload)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    uploadAvatar.mutate(file)
    setAvatarMenuOpen(false)
    // Reset input so same file can be selected again
    e.target.value = ''
  }

  const handleDeleteAvatar = () => {
    deleteAvatar.mutate()
    setAvatarMenuOpen(false)
  }

  const isUploadingAvatar = uploadAvatar.isPending || deleteAvatar.isPending

  return (
    <div className="p-6 sm:p-8 max-w-3xl mx-auto space-y-8">
      {/* Header with avatar */}
      <div className="flex items-center gap-5">
        <div className="relative group">
          <div className={cn(
            'flex h-20 w-20 items-center justify-center rounded-2xl shadow-md overflow-hidden',
            !avatarSrc && 'bg-gradient-to-br from-primary to-purple-600',
          )}>
            {isUploadingAvatar ? (
              <Loader2 className="h-6 w-6 text-white animate-spin" />
            ) : avatarSrc ? (
              <img src={avatarSrc} alt={user.full_name} className="h-full w-full object-cover" />
            ) : (
              <span className="text-white text-3xl font-bold">{initial}</span>
            )}
          </div>

          {/* Camera overlay */}
          <button
            type="button"
            onClick={() => setAvatarMenuOpen((o) => !o)}
            className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/0 group-hover:bg-black/40 transition-all cursor-pointer"
          >
            <Camera className="h-5 w-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>

          {/* Avatar dropdown menu */}
          {avatarMenuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setAvatarMenuOpen(false)} />
              <div className="absolute left-0 top-full mt-2 z-20 w-48 rounded-xl border border-slate-200 bg-white shadow-lg py-1 overflow-hidden">
                <button
                  onClick={() => { fileInputRef.current?.click(); setAvatarMenuOpen(false) }}
                  className="flex items-center gap-2.5 w-full px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <Camera className="h-4 w-4 text-primary" />
                  Subir foto
                </button>
                {avatarSrc && (
                  <button
                    onClick={handleDeleteAvatar}
                    className="flex items-center gap-2.5 w-full px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                    Eliminar foto
                  </button>
                )}
              </div>
            </>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={handleFileChange}
          />

          {uploadAvatar.isError && (
            <p className="absolute -bottom-6 left-0 text-xs text-red-500 whitespace-nowrap">
              {uploadAvatar.error?.message ?? 'Error al subir'}
            </p>
          )}
        </div>

        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-slate-900 truncate">{user.full_name}</h1>
          <p className="text-sm text-slate-500 truncate">{user.email}</p>
          <div className="flex gap-2 mt-1.5">
            {user.roles.map((r) => (
              <span key={r.id} className="text-xs bg-primary/15 text-primary rounded-full px-2.5 py-0.5 font-medium">
                {r.name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Personal info form */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-800 mb-5 flex items-center gap-2">
          <Pencil className="h-4 w-4 text-primary" /> Información personal
        </h2>
        <form
          onSubmit={profileForm.handleSubmit(handleProfileSubmit)}
          className="space-y-5"
        >
          {/* Row 1: Name + Username */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>
                Nombre completo <span className="text-red-400">*</span>
              </label>
              <input {...profileForm.register('full_name')} className={inputCls} />
              {profileForm.formState.errors.full_name && (
                <p className="text-xs text-red-500 mt-1">{profileForm.formState.errors.full_name.message}</p>
              )}
            </div>
            <div>
              <label className={labelCls}>
                Usuario <span className="text-red-400">*</span>
              </label>
              <input {...profileForm.register('username')} className={inputCls} />
              {profileForm.formState.errors.username && (
                <p className="text-xs text-red-500 mt-1">{profileForm.formState.errors.username.message}</p>
              )}
            </div>
          </div>

          {/* Row 2: Email + Phone */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={cn(labelCls, 'flex items-center gap-1.5')}>
                <Mail className="h-3.5 w-3.5" /> Email <span className="text-red-400">*</span>
              </label>
              <input {...profileForm.register('email')} type="email" className={inputCls} />
              {profileForm.formState.errors.email && (
                <p className="text-xs text-red-500 mt-1">{profileForm.formState.errors.email.message}</p>
              )}
            </div>
            <div>
              <label className={cn(labelCls, 'flex items-center gap-1.5')}>
                <Phone className="h-3.5 w-3.5" /> Teléfono
              </label>
              <input
                {...profileForm.register('phone')}
                type="tel"
                className={inputCls}
                placeholder="+57 300 123 4567"
              />
            </div>
          </div>

          {/* Row 3: Company + Job title */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={cn(labelCls, 'flex items-center gap-1.5')}>
                <Building2 className="h-3.5 w-3.5" /> Empresa
              </label>
              <input
                {...profileForm.register('company')}
                className={inputCls}
                placeholder="Mi Empresa S.A.S"
              />
            </div>
            <div>
              <label className={cn(labelCls, 'flex items-center gap-1.5')}>
                <Briefcase className="h-3.5 w-3.5" /> Cargo
              </label>
              <input
                {...profileForm.register('job_title')}
                className={inputCls}
                placeholder="Gerente de logística"
              />
            </div>
          </div>

          {/* Bio */}
          <div>
            <label className={labelCls}>Bio</label>
            <textarea
              {...profileForm.register('bio')}
              rows={3}
              className={cn(inputCls, 'resize-none')}
              placeholder="Cuéntanos sobre ti..."
              maxLength={500}
            />
            <p className="text-xs text-slate-400 mt-0.5 text-right">
              {(profileForm.watch('bio') ?? '').length}/500
            </p>
          </div>

          {/* Row 4: Timezone + Language */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={cn(labelCls, 'flex items-center gap-1.5')}>
                <Globe className="h-3.5 w-3.5" /> Zona horaria
              </label>
              <select {...profileForm.register('timezone')} className={inputCls}>
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={cn(labelCls, 'flex items-center gap-1.5')}>
                <Languages className="h-3.5 w-3.5" /> Idioma
              </label>
              <select {...profileForm.register('language')} className={inputCls}>
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2 border-t border-slate-100">
            <button
              type="submit"
              disabled={updateProfile.isPending || !profileForm.formState.isDirty}
              className={cn(
                'rounded-xl px-5 py-2.5 text-sm font-semibold text-white transition-all shadow-sm',
                profileForm.formState.isDirty
                  ? 'bg-primary hover:bg-primary/90 hover:shadow-md'
                  : 'bg-slate-300 cursor-not-allowed',
              )}
            >
              {updateProfile.isPending ? 'Guardando...' : 'Guardar cambios'}
            </button>
            {updateProfile.isSuccess && (
              <span className="text-sm text-emerald-600 font-medium">Cambios guardados</span>
            )}
            {updateProfile.error && (
              <span className="text-sm text-red-600">{updateProfile.error.message}</span>
            )}
          </div>
        </form>
      </div>

      {/* Password form */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-800 mb-4">Cambiar contraseña</h2>
        <form
          onSubmit={passwordForm.handleSubmit((data) =>
            changePassword.mutate(
              { current_password: data.current_password, new_password: data.new_password },
              { onSuccess: () => passwordForm.reset() },
            )
          )}
          className="space-y-4"
        >
          <div>
            <label className={labelCls}>Contraseña actual</label>
            <input
              {...passwordForm.register('current_password')}
              type="password"
              className={inputCls}
            />
            {passwordForm.formState.errors.current_password && (
              <p className="text-xs text-red-500 mt-1">{passwordForm.formState.errors.current_password.message}</p>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Nueva contraseña</label>
              <input
                {...passwordForm.register('new_password')}
                type="password"
                className={inputCls}
              />
              {passwordForm.formState.errors.new_password && (
                <p className="text-xs text-red-500 mt-1">{passwordForm.formState.errors.new_password.message}</p>
              )}
            </div>
            <div>
              <label className={labelCls}>Confirmar nueva</label>
              <input
                {...passwordForm.register('confirm_password')}
                type="password"
                className={inputCls}
              />
              {passwordForm.formState.errors.confirm_password && (
                <p className="text-xs text-red-500 mt-1">{passwordForm.formState.errors.confirm_password.message}</p>
              )}
            </div>
          </div>
          {changePassword.error && (
            <p className="text-sm text-red-600">{changePassword.error.message}</p>
          )}
          <div className="flex items-center gap-3 pt-2 border-t border-slate-100">
            <button
              type="submit"
              disabled={changePassword.isPending}
              className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60 transition-all shadow-sm hover:shadow-md"
            >
              {changePassword.isPending ? 'Cambiando...' : 'Cambiar contraseña'}
            </button>
            {changePassword.isSuccess && (
              <span className="text-sm text-emerald-600 font-medium">Contraseña actualizada</span>
            )}
          </div>
        </form>
      </div>

      {/* Account info (read-only) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-800 mb-4">Información de la cuenta</h2>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <div>
            <dt className="text-slate-500">ID</dt>
            <dd className="font-mono text-slate-800 text-xs mt-0.5">{user.id}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Tenant</dt>
            <dd className="text-slate-800 mt-0.5">{user.tenant_id}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Estado</dt>
            <dd className="mt-0.5">
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {user.is_active ? 'Activo' : 'Inactivo'}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Superusuario</dt>
            <dd className="text-slate-800 mt-0.5">{user.is_superuser ? 'Sí' : 'No'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Creado</dt>
            <dd className="text-slate-800 mt-0.5">{new Date(user.created_at).toLocaleDateString('es-CO')}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Actualizado</dt>
            <dd className="text-slate-800 mt-0.5">{new Date(user.updated_at).toLocaleDateString('es-CO')}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
