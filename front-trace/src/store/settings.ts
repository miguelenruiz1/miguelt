import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type SolanaCluster = 'devnet' | 'mainnet-beta'

interface SettingsStore {
  solanaCluster: SolanaCluster
  setSolanaCluster: (c: SolanaCluster) => void
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      solanaCluster: 'devnet',
      setSolanaCluster: (c) => set({ solanaCluster: c }),
    }),
    { name: 'trace-settings' },
  ),
)

export function explorerAddressUrl(pubkey: string, cluster: SolanaCluster) {
  return `https://explorer.solana.com/address/${pubkey}?cluster=${cluster}`
}

export function explorerTxUrl(sig: string, cluster: SolanaCluster) {
  return `https://explorer.solana.com/tx/${sig}?cluster=${cluster}`
}

/** XRAY by Helius — viewer for cNFTs with full metadata + image */
export function xrayAssetUrl(assetId: string, cluster: SolanaCluster) {
  const net = cluster === 'mainnet-beta' ? '' : '?network=devnet'
  return `https://xray.helius.xyz/token/${assetId}${net}`
}

/** XRAY transaction viewer */
export function xrayTxUrl(sig: string, cluster: SolanaCluster) {
  const net = cluster === 'mainnet-beta' ? '' : '?network=devnet'
  return `https://xray.helius.xyz/tx/${sig}${net}`
}
