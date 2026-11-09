# MyEdenred for Home Assistant

Unofficial [MyEdenred Portugal](https://www.myedenred.pt/) integration for Home Assistant.

[![Release](https://img.shields.io/github/v/release/rbaptista1995/MyEdenred?style=for-the-badge&label=Release&color=blue)](https://github.com/rbaptista1995/MyEdenred/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/rbaptista1995/MyEdenred/myedenred.zip?style=for-the-badge&label=Downloads&color=brightgreen)](https://github.com/rbaptista1995/MyEdenred/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Repository-orange?style=for-the-badge)](https://hacs.xyz/)
[![License](https://img.shields.io/github/license/rbaptista1995/MyEdenred?style=for-the-badge)](LICENSE)
[![HACS validation](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hacs.yml/badge.svg)](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hassfest.yml/badge.svg)](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hassfest.yml)

> **About the download count:** the badge above counts downloads of the
> `myedenred.zip` release asset across all releases. It measures file
> downloads — HACS installs, updates and reinstalls all count — and it is
> **not** a count of unique users or active installations.

## Features

- Balance and transaction sensors for each MyEdenred card
- Readable sub-entities per card: last transaction (merchant, town, amount), spent this month, last top-up, card status, and a transaction event for automations
- Config-flow UI setup (username, password and 2FA code received by e-mail)
- Multiple cards supported — add the integration once per card
- Portuguese (PT) country targeting

## Installation

### HACS

The repository is not (yet) part of the HACS default repository, so add it
once as a custom repository:

1. Open **HACS** in Home Assistant
2. Click **⋮ → Custom repositories**
3. Add the repository URL:
   `https://github.com/rbaptista1995/MyEdenred`
4. Select category **Integration**
5. Search for **MyEdenred** and install it
6. Restart Home Assistant

Once included in the HACS default repository, MyEdenred can be searched
directly in HACS without adding a custom repository.

### Manual

1. Download `myedenred.zip` from the
   [latest release](https://github.com/rbaptista1995/MyEdenred/releases/latest)
2. Extract its contents into `config/custom_components/myedenred/`
3. Restart Home Assistant

## Configuration

1. Navigate to **Settings → Devices & Services** and click **Add Integration**
2. Search for **MyEdenred**
3. Enter your credentials
4. Enter the 2FA code received by e-mail
5. Repeat the procedure for each additional card you own

## Entities

Each card is a device with these entities:

| Entity | What it shows |
|---|---|
| `sensor.edenred_card_<number>` | Balance. Unchanged: same name, id and attributes (`ownerName`, `cardStatus`, `cardNumber`, `transactions`) as before, so existing dashboards and automations keep working. |
| Card status *(diagnostic)* | `active`, … as reported by MyEdenred |
| Last transaction | Amount of the latest transaction (negative for purchases), with `date`, `kind` (`purchase`, `top_up`, `refund`, `other`), `merchant`, `location` and `description` attributes |
| Last transaction time | When it happened (timestamp) |
| Spent this month | Purchases minus refunds in the current month |
| Last top-up | Amount of the latest top-up, with its `date` |
| Transaction *(event)* | Fires `purchase` / `top_up` / `refund` / `other` once for every new transaction, with the same attributes. Shows up in the logbook and can trigger automations. Transactions already listed when Home Assistant starts are not replayed. |

The transaction entities are only created when *Include the transaction list* was
ticked during setup.

Example automation, a notification for every top-up:

```yaml
triggers:
  - trigger: state
    entity_id: event.edenred_card_1234_transaction
    not_from: unavailable
conditions:
  - condition: state
    entity_id: event.edenred_card_1234_transaction
    attribute: event_type
    state: top_up
actions:
  - action: notify.notify
    data:
      message: >-
        Edenred top-up: {{ state_attr(trigger.entity_id, 'amount') }} €
```

## Cards

Add any entity card as usual.

### Transactions

While showing the card's balance on a card is commonplace (any entity card
will do), displaying transactions can be more complicated to achieve.

#### Using the built-in Markdown card

No custom card needed. Replace the entity id with yours:

```yaml
type: markdown
content: |
  | Date | Where | € |
  |:--|:--|--:|
  {% for t in (state_attr('sensor.edenred_card_XXXXXXX', 'transactions') or [])[:10] -%}
  {%- set d = as_datetime(t.date) -%}
  {%- if t.name.startswith('Compra') -%}
  {%- set body = t.name.split(':', 1)[1][1:] -%}
  {%- set where = (body[:20] | trim | title) ~ ' · ' ~ (body[20:] | trim | regex_replace('^\\d{4}-\\d{3}\\s*', '') | title) -%}
  {%- else -%}{%- set where = '💰 ' ~ t.name -%}{%- endif -%}
  | {{ as_local(d).strftime('%d/%m %H:%M') if d else t.date[:10] }} | {{ where }} | {{ '%+.2f' | format(t.amount) }} |
  {% endfor %}
```

#### Using a custom:html-template-card

You can use a [custom:html-template-card](https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-Jinja2-Template-card) to display your data like this:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Cartão Refeição
    entities:
      - entity: sensor.edenred_card_XXXXXXX
        secondary_info: last-updated
        icon: mdi:credit-card
      - entity: sensor.edenred_card_XXXXXXX
        type: custom:multiple-entity-row
        name: Nome Cartão
        show_state: false
        entities:
          - attribute: ownerName
      - entity: sensor.edenred_card_XXXXXXX
        type: custom:multiple-entity-row
        name: Estado Cartão
        show_state: false
        entities:
          - attribute: cardStatus
  - type: custom:html-template-card
    ignore_line_breaks: true
    content: |
      <table
        style="padding: 0px;border-collapse:separate;
        border:solid gray 1px;
        border-radius:6px;  ">
      <tr>
        <td  colspan="3"><center><font color="#6B8E23" size=4> <b>Últimos Movimentos: </b></center> </font></td>
      </tr>
      <tr>

      </tr>

       <tr>
          <th style="width:10%;"><u><font color=orange>Data</font></u></th>
          <th style="width:65%;"><u><font color=orange>Descrição</font></u></th>
          <th style="width:25%;"><u><font color=orange>Valor</font></u></th>
        </tr> {% for t in state_attr('sensor.edenred_card_XXXXXXX','transactions') %}

         <tr>
         <td style="border-top: 1px solid #dddddd;  text-align: center;">{{t.date}}</td>
         <td style="border-top: 1px solid #dddddd;   text-align: center;">{{t.name}}</td>
         <td style="border-top: 1px solid #dddddd;   text-align: center;"><b>{{t.amount}}</b></td>
      </div></td>
        </tr>{% endfor}</table>
```

(credits thanks to [Vítor Nóbrega](https://forum.cpha.pt/u/vpnobrega/summary)).

#### Using a custom:list-card

Another alternative is to use [custom:list-card](https://github.com/iantrich/list-card) which has the advantage of being able to indicate the number of rows to display:

```yaml
type: custom:list-card
entity: sensor.edenred_card_XXXXXXX
feed_attribute: transactions
title: MyEdenred Transactions
row_limit: 10
columns:
  - title: Data
    field: date
  - title: Movimento
    field: name
  - title: Valor
    field: amount
    postfix: ' €'
    style:
      - text-align: right
      - white-space: nowrap
```

#### Using a custom:browser-mod

If you have [custom:browser-mod](https://github.com/thomasloven/hass-browser_mod) in your system, you can show the transactions in a nice popup window, like this:
(this also uses [custom:mushroom-entity-card](https://github.com/piitaya/lovelace-mushroom) and [custom:list-card](https://github.com/iantrich/list-card))

```yaml
type: custom:mushroom-entity-card
entity: sensor.edenred_card_XXXXXXX
name: Cartão Refeição
tap_action:
    action: fire-dom-event
    browser_mod:
        command: popup
        title: MyEdenred Transactions
        style:
            .: |
            :host .content {
                width: calc(800px);
                align: center;
            }
        card:
            type: custom:list-card
            entity: sensor.edenred_card_XXXXXXX
            feed_attribute: transactions
            row_limit: 20
            columns:
            - title: Data
                field: date
            - title: Movimento
                field: name
            - title: Valor
                field: amount
                postfix: ' €'
                style:
                - text-align: right
                - white-space: nowrap
            style: |
            tr {
                height: 25px
            }
```

## Releases

Every GitHub release is automatically packaged by CI into a single
`myedenred.zip` asset containing the integration files. HACS installs and
updates from that asset.

## Legal notice

This is a personal project and isn't in any way affiliated with, sponsored
or endorsed by [MyEdenred Portugal](https://www.myedenred.pt/).

All product names, trademarks and registered trademarks in (the images in)
this repository are property of their respective owners. All images in this
repository are used by the project for identification purposes only.

The author of this project categorically rejects any and all responsibility
for the card balance and other data presented by the integration.
