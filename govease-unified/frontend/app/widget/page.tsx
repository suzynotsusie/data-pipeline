import { CitizenAssistant } from "../../components/CitizenAssistant";
import { getCitizenWorkflowCatalog } from "../../lib/citizen-catalog";

export default async function WidgetPage() {
  const catalog = await getCitizenWorkflowCatalog();

  return (
    <main className="widget-page">
      <CitizenAssistant compact groups={catalog.groups} />
    </main>
  );
}
