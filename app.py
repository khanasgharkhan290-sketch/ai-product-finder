        st.error("Missing API key(s): " + ", ".join(missing))
        st.markdown(
            "Set them in `.streamlit/secrets.toml` locally or in "
            "Streamlit Community Cloud → **App settings → Secrets**. "
            "Do not commit secrets to GitHub."
        )
        return

    budget = budget_input if budget_input > 0 else None
    search_query = request_text.strip()
    if budget is not None:
        search_query += f" under {currency} {budget:g}"
    if preferences.strip():
        search_query += " " + preferences.strip()

    try:
        with st.spinner("Searching live shopping listings…"):
            listings = search_products(
                search_query, serpapi_key, country, language, max_results
            )
        if not listings:
            st.warning(
                "The shopping search returned no listings. Try a broader product "
                "description or a different shopping market."
            )
            return

        st.subheader(f"Retrieved listings ({len(listings)})")
        st.caption("Prices, ratings, and seller details below are shown as returned by the shopping API.")
        for index, item in enumerate(listings, start=1):
            with st.container(border=True):
                image_col, details_col = st.columns([1, 3])
                with image_col:
                    if item.get("thumbnail"):
                        st.image(item["thumbnail"], use_container_width=True)
                with details_col:
                    st.markdown(f"**{index}. {safe_text(item.get('title'), 'Untitled listing')}**")
                    price = item.get("price")
                    st.write(f"**Price:** {price if price else 'Not provided by source'}")
                    st.write(f"**Seller/source:** {safe_text(item.get('source'))}")
                    if item.get("rating") is not None:
                        rating = item["rating"]
                        reviews = item.get("reviews")
                        suffix = f" ({reviews} reviews)" if reviews is not None else ""
                        st.write(f"**Source-reported rating:** {rating}{suffix}")
                    if item.get("delivery"):
                        st.write(f"**Delivery text from source:** {item['delivery']}")
                    if item.get("snippet"):
                        st.write(item["snippet"])
                    if item.get("link"):
                        st.link_button("Open seller/listing", item["link"])

        with st.spinner("Gemini is preparing a cautious comparison…"):
            client = genai.Client(api_key=gemini_key)
            analysis = make_comparison(
                client,
                DEFAULT_MODEL,
                request_text.strip(),
                budget,
                currency,
                preferences.strip(),
                listings,
            )

        st.divider()
        st.subheader("AI-assisted comparison")
        st.write(safe_text(analysis.get("summary"), "No summary was returned."))

        by_id = {item.get("id"): item for item in analysis.get("products", []) if isinstance(item, dict)}
        for index, listing in enumerate(listings, start=1):
            info = by_id.get(index, {})
            with st.expander(f"{index}. {safe_text(listing.get('title'), 'Product')} — {safe_text(info.get('verdict'), 'Comparison details')}"):
                st.markdown("**Fit for your needs**")
                st.write(safe_text(info.get("fit")))
                st.markdown("**Key features**")
                features = info.get("key_features") or ["Not provided by source"]
                for feature in features:
                    st.markdown(f"- {feature}")
                st.markdown("**Advantages**")
                advantages = info.get("advantages") or ["Not enough source information to assess."]
                for advantage in advantages:
                    st.markdown(f"- {advantage}")
                st.markdown("**Disadvantages / caveats**")
                disadvantages = info.get("disadvantages") or ["Verify specifications with the seller."]
                for disadvantage in disadvantages:
                    st.markdown(f"- {disadvantage}")
                st.markdown("**Specifications**")
                specs = info.get("specifications")
                if isinstance(specs, dict) and specs:
                    st.table(
                        [{"Specification": key, "Value": value} for key, value in specs.items()]
                    )
                else:
                    st.write("Specifications were not provided in the source listing.")
                st.caption("The AI summary is generated from listing information and may be incomplete.")

        notes = analysis.get("comparison_notes") or []
        if notes:
            st.subheader("Comparison notes")
            for note in notes:
                st.markdown(f"- {note}")
        questions = analysis.get("follow_up_questions") or []
        if questions:
            st.subheader("Questions that could improve the match")
            for question in questions:
                st.markdown(f"- {question}")

        st.warning(
            "Shopping listings, prices, seller terms, and availability can change. "
            "Confirm the final price, exact model/SKU, specifications, shipping, and "
            "return policy on the seller's page before buying."
        )

    except requests.HTTPError as exc:
        st.error(f"The shopping API returned an HTTP error: {exc}")
    except requests.RequestException as exc:
        st.error(f"Could not reach the shopping API: {exc}")
    except json.JSONDecodeError:
        st.error("Gemini returned a response that could not be parsed. Please try again.")
    except Exception as exc:
        st.error(f"Something went wrong: {exc}")
        st.caption("Check that your API keys are valid and that your Gemini/SerpApi quotas are available.")


if __name__ == "__main__":
    main()
