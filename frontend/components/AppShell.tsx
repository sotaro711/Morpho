"use client";

import { usePathname } from "next/navigation";

import { AppSidebar, NAV_ITEMS, normalizePath } from "@/components/AppSidebar";
import { SimulatorProvider } from "@/components/SimulatorProvider";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

/** ログイン後の画面の枠。左にページを切り替えるサイドバー、右に各ページ。 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = normalizePath(usePathname());
  const title = NAV_ITEMS.find((item) => item.href === pathname)?.label;

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
            <h1 className="text-sm font-semibold">{title}</h1>
          </header>
          <SimulatorProvider>{children}</SimulatorProvider>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
