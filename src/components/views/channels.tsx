import { FormEvent, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { HudKicker, HudPanel } from "@/components/hud/panel";
import { useAdmin } from "@/lib/admin-store";

export function ChannelsView() {
  const channels = useAdmin((s) => s.channels);
  const addChannel = useAdmin((s) => s.addChannel);
  const removeChannel = useAdmin((s) => s.removeChannel);
  const [chat, setChat] = useState("");
  const [invite, setInvite] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!chat.trim()) return;
    addChannel(chat.trim(), invite.trim());
    setChat("");
    setInvite("");
    toast.success("Force-sub channel saved");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <HudKicker>Channels</HudKicker>
        <h1 className="mt-1 font-display text-2xl font-semibold">Force-sub</h1>
      </header>
      <ul className="space-y-2">
        {channels.map((channel) => (
          <li key={channel.chat_id}>
            <HudPanel className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{channel.chat_id}</p>
                <p className="truncate font-display text-xs tracking-widest text-muted-foreground">{channel.invite_url}</p>
              </div>
              <Button variant="danger" size="sm" onClick={() => removeChannel(channel.chat_id)}>
                Remove
              </Button>
            </HudPanel>
          </li>
        ))}
      </ul>
      <HudPanel>
        <form onSubmit={onSubmit} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <Input placeholder="channel id or @username" value={chat} onChange={(e) => setChat(e.target.value)} />
          <Input placeholder="invite url, optional" value={invite} onChange={(e) => setInvite(e.target.value)} />
          <Button type="submit">Add</Button>
        </form>
      </HudPanel>
    </div>
  );
}
