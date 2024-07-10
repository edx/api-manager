API Strategy and Change Management Process
=============================================

Status
------

Draft


Context
-------

As enterprise APIs evolve, we need to ensure that changes are introduced in a backward-compatible manner that doesn't break existing clients, and that we have a clear and consistent process for handling these changes.

Solution Approach
-----------------

By adopting an API change management process, we can ensure that our API evolves in a controlled and predictable manner. This approach will ensure minimal disruptions and provide a clear approach on how to handle upstream changes to Enterprise APIs. The API change management process includes the following components:

- Guidelines around API versioning
- Guidelines around dealing with breaking changes
- Communicating upstream changes internally and externally


Decision
--------

**API Versioning**

- Currently, we use URI versioning in all external and internal APIs. We will continue to use this approach as it's simple and doesn't require a lot of customization on client's end. Begin with version (v1) when the API is initially released.
- A new API version should only be introduced if the change is not backwards-compatible. Changes such as modifying request/response formats, removing fields, altering endpoints, or changing authentication methods are some scenarios where releasing a new version will make sense.

**Guidelines around how to deal with breaking changes**

- Breaking changes should be avoided whenever possible.
- Breaking changes should be brought to Solution Review (Enterprise) with representation from Iris team.
- If a breaking change is necessary, it should be introduced in a new version of the API, and the old version should be deprecated.
- Deprecated versions of the API should be maintained for a reasonable period of time (e:g 6-12 months depending on the impact) to allow clients to migrate to the new version.
- After the deprecation period, we should discontinue the support of the older version from production.

**Communicate upstream changes internally and externally**

- To communicate the impact of upstream changes within enterprise teams:
    - Request feedback from Team Iris on all relevant API changes including key stakeholders as reviewers (technical lead and product manager).
    - We can also create a Slack channel #enterprise-api-updates for better tracking, and to discuss any upcoming change, the rationale behind it, classify as breaking or non-breaking, and its impact.
    - For major changes, communicate to Iris before deployment so they can prepare for next steps (updating docs and informing clients if required). Rigorously test the changes.

- To communicate the impact to clients and enterprise customers:
    - Clients should be notified beforehand about the deprecation plans and their timelines through documentation and through other appropriate channels.
    - Docs should clearly reflect all changes to the APIs (breaking and non-breaking).
    - In case of a version update, document all breaking changes in detail, including migration guides to assist clients in updating their integrations.
    - Iris will maintain an API changelog for all external APIs, specifically those with more than ~5 clients. This changelog will be available in the Developer Documentation, which is currently being developed by Team Iris.
    - API changelog will include a timeline of monthly updates to all the relevant APIs that have undergone any changes.


Consequences
------------

- Overhead: Maintaining multiple versions of the API can increase the maintenance burden of the API.

Alternatives considered
-----------------------
- **Semantic Versioning:**
    Although this standardized approach is widely used in the industry to track breaking, major, and minor changes, it will become challenging to manage the versions of all APIs as we scale up.