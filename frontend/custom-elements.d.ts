import type { DetailedHTMLProps, HTMLAttributes, CSSProperties } from 'react'

declare global {
  namespace React {
    namespace JSX {
      interface IntrinsicElements {
        'model-viewer': DetailedHTMLProps<
          HTMLAttributes<HTMLElement> & {
            src: string
            alt?: string
            'auto-rotate'?: boolean
            'camera-controls'?: boolean
            style?: CSSProperties
          },
          HTMLElement
        >
      }
    }
  }
}

export {}