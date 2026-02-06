"use client";

import { useParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Construction } from "lucide-react";

export default function SessionPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-warning/20">
            <Construction className="h-8 w-8 text-warning" />
          </div>
          <CardTitle className="text-2xl font-bold">Session Page Coming Soon</CardTitle>
          <CardDescription>
            The active session experience is still being built.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="bg-muted rounded-lg p-4 text-center">
            <p className="text-sm text-muted-foreground">
              Session ID: <code className="text-xs bg-background px-2 py-1 rounded">{sessionId}</code>
            </p>
          </div>

          <p className="text-sm text-muted-foreground text-center">
            This page will include the 55-minute session timer, audio controls,
            participant avatars, and the peer review interface.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
