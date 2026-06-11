interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  action?: React.ReactNode;
}

export function SectionHeader({ title, subtitle, badge, action }: SectionHeaderProps) {
  return (
    <div className="flex items-end justify-between gap-4 mb-4">
      <div>
        <div className="flex items-center gap-2.5">
          <h2 className="text-base font-semibold tracking-tight">{title}</h2>
          {badge}
        </div>
        {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
