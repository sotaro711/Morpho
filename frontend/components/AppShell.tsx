"use client";

import { usePathname } from "next/navigation";

import { AppSidebar, NAV_ITEMS, normalizePath } from "@/components/AppSidebar";
import { MaterialsProvider } from "@/components/MaterialsProvider";
import { Simulator3DProvider } from "@/components/Simulator3DProvider";
import { SimulatorProvider } from "@/components/SimulatorProvider";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

/** ログイン後の画面の枠。左にページを切り替えるサイドバー、右に各ページ。 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = normalizePath(usePathname());
  const page = NAV_ITEMS.find((item) => item.href === pathname);
  const title = page && ("title" in page ? page.title : page.label);

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <h1 className="text-sm font-semibold">{title}</h1>
          </header>
          <MaterialsProvider>
            <SimulatorProvider>
              <Simulator3DProvider>{children}</Simulator3DProvider>
            </SimulatorProvider>
          </MaterialsProvider>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
