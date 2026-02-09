"use client";

interface RoomAmbientAnimationProps {
  roomType: string;
}

export function RoomAmbientAnimation({ roomType }: RoomAmbientAnimationProps) {
  switch (roomType) {
    case "cozy-study":
      return <CozyStudyAmbient />;
    case "coffee-shop":
      return <CoffeeShopAmbient />;
    case "library":
      return <LibraryAmbient />;
    default:
      return null;
  }
}

function CozyStudyAmbient() {
  return (
    <div
      className="absolute inset-0 z-[5] pointer-events-none"
      style={{
        background:
          "radial-gradient(ellipse 300px 200px at 50% 30%, rgba(212, 165, 116, 0.25), transparent)",
        animation: "lamp-flicker 2s ease-in-out infinite",
      }}
    />
  );
}

function CoffeeShopAmbient() {
  return (
    <div className="absolute inset-0 z-[5] pointer-events-none overflow-hidden">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            width: "8px",
            height: "16px",
            background: "rgba(255, 255, 255, 0.3)",
            filter: "blur(4px)",
            bottom: "35%",
            left: `${25 + i * 20}%`,
            animation: `steam-rise ${3 + i * 0.5}s ease-out infinite`,
            animationDelay: `${i * 1.2}s`,
          }}
        />
      ))}
    </div>
  );
}

function LibraryAmbient() {
  return (
    <div
      className="absolute inset-0 z-[5] pointer-events-none"
      style={{
        background:
          "repeating-linear-gradient(180deg, transparent, transparent 20px, rgba(180, 200, 220, 0.12) 20px, rgba(180, 200, 220, 0.12) 21px)",
        animation: "rain-fall 4s linear infinite",
        opacity: 0.12,
      }}
    />
  );
}
