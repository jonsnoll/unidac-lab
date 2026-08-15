import './DeviceIcon.css'


function iconType(device) {
  const id = (
    device?.id ||
    device?.deviceId ||
    ''
  ).toLowerCase()

  const vendor = (
    device?.vendor ||
    ''
  ).toLowerCase()

  const category = (
    device?.category ||
    ''
  ).toLowerCase()

  const kind = (
    device?.kind ||
    ''
  ).toLowerCase()


  if (
    id.includes('windows')
  ) {
    return 'windows'
  }

  if (
    id === 'cloud-nat' ||
    kind === 'cloud'
  ) {
    return 'cloud'
  }

  if (
    id === 'network' ||
    kind === 'network'
  ) {
    return 'network'
  }

  if (
    vendor === 'fortinet'
  ) {
    return 'firewall'
  }

  if (
    category === 'endpoint'
  ) {
    return 'endpoint'
  }

  return 'appliance'
}


function DeviceIcon({
  device,
  variant = 'palette',
}) {
  const type = iconType(device)

  return (
    <span
      className={
        `device-symbol device-symbol-${type} device-symbol-${variant}`
      }
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 32 32"
        focusable="false"
      >
        {type === 'cloud' && (
          <>
            <path
              d="M9 24h14.5a5.5 5.5 0 0 0 .7-10.95A8.5 8.5 0 0 0 8.1 11.2 6.5 6.5 0 0 0 9 24Z"
            />
            <path
              d="M12 19h8"
            />
          </>
        )}

        {type === 'network' && (
          <>
            <rect
              x="4"
              y="8"
              width="24"
              height="16"
              rx="3"
            />
            <circle cx="9" cy="16" r="1.2" />
            <circle cx="14" cy="16" r="1.2" />
            <circle cx="19" cy="16" r="1.2" />
            <circle cx="24" cy="16" r="1.2" />
            <path d="M8 12h16M8 20h16" />
          </>
        )}

        {type === 'firewall' && (
          <>
            <rect
              x="4"
              y="6"
              width="24"
              height="20"
              rx="2"
            />
            <path
              d="M4 12h24M4 19h24M10 6v6M21 6v6M15 12v7M9 19v7M22 19v7"
            />
          </>
        )}

        {type === 'endpoint' && (
          <>
            <rect
              x="5"
              y="5"
              width="22"
              height="16"
              rx="2"
            />
            <path
              d="M12 26h8M16 21v5"
            />
          </>
        )}

        {type === 'windows' && (
          <>
            <rect
              x="5"
              y="5"
              width="22"
              height="22"
              rx="2"
            />
            <path
              d="M16 5v22M5 16h22"
            />
          </>
        )}

        {type === 'appliance' && (
          <>
            <rect
              x="6"
              y="4"
              width="20"
              height="24"
              rx="3"
            />
            <path
              d="M10 10h8M10 16h8M10 22h8"
            />
            <circle cx="22" cy="10" r="1" />
            <circle cx="22" cy="16" r="1" />
            <circle cx="22" cy="22" r="1" />
          </>
        )}
      </svg>
    </span>
  )
}


export default DeviceIcon
