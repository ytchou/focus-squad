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
  return <div className="absolute inset-0 z-[5] pointer-events-none ambient-lamp" />;
}

function CoffeeShopAmbient() {
  return (
    <div className="absolute inset-0 z-[5] pointer-events-none overflow-hidden">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="absolute rounded-full ambient-steam-wisp"
          style={{
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
  return <div className="absolute inset-0 z-[5] pointer-events-none ambient-rain" />;
}
